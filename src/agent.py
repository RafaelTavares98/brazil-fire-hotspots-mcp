"""The agent: a model that answers questions by calling the MCP tools.

The model chooses tools and writes the sentence. It never produces a
number of its own. Every number in its sentence must appear in what the
tools answered, or in the question itself; otherwise the sentence is
thrown away and code says what the tools found.
"""

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from mcp.client.client import Client

#: The most times the model is asked within one question.
MOST_ROUNDS = 4

SYSTEM = (
    'You answer questions about fires in Brazil using the tools. Every '
    'number you write must be copied from a tool result: never estimate, '
    'never compute a number yourself. If the tools cannot answer, say so '
    'in one sentence. Answer in the language of the question, in one or '
    'two sentences, and name the period and the place the number covers. '
    'If a tool result carries warnings, mention them.')

_NUMBER = re.compile(r'\d(?:[\d.,]*\d)?')


class Call:
    """One tool call the model made, and what came back."""

    def __init__(self, name, arguments, result, failed):
        self.name = name
        self.arguments = arguments
        self.result = result
        self.failed = failed


class AgentAnswer:
    def __init__(self, text, calls, rejected, draft=''):
        self.text = text
        self.calls = calls
        self.rejected = rejected
        #: What the model wrote, kept even when it was thrown away.
        self.draft = draft


def _decimal(text):
    try:
        return Decimal(text).normalize()
    except InvalidOperation:
        return None


def _readings(token):
    """Every value a written number can mean.

    278,299 is English for 278299; 1.625 and 73,5 are Portuguese for
    1625 and 73.5. A sentence may be in either language, so a number
    passes when any reading of it was computed.
    """
    english = _decimal(token.replace(',', ''))
    brazilian = _decimal(token.replace('.', '').replace(',', '.'))
    return {english, brazilian} - {None}


def _computed(text):
    """The numbers in tool output, which is always JSON, so English."""
    return {_decimal(token.replace(',', ''))
            for token in _NUMBER.findall(text)} - {None}


def invented(text, sources, question=''):
    """The numbers in text that no source and not the question contain."""
    allowed = set()
    for written in [question, *sources]:
        allowed |= _computed(written)
        for token in _NUMBER.findall(written):
            allowed |= _readings(token)
    return [token for token in _NUMBER.findall(text)
            if not _readings(token) & allowed]


def _spec(tool):
    """An MCP tool, in the shape a chat model's tool list takes."""
    return {'type': 'function', 'function': {
        'name': tool.name, 'description': tool.description,
        'parameters': tool.input_schema}}


def _fallback(calls):
    """What code says when the model's sentence cannot be trusted."""
    good = [call for call in calls if not call.failed]
    if not good:
        return ('No tool gave an answer, so no number can be stated. Ask '
                'again with a place and a period.')
    last = good[-1]
    value = json.loads(last.result)['value']
    return f'The tool {last.name} answered: {json.dumps(value)}.'


async def _call(client, request):
    function = request['function']
    arguments = json.loads(function['arguments'] or '{}')
    result = await client.call_tool(function['name'], arguments)
    return Call(function['name'], arguments, result.content[0].text,
                bool(result.is_error))


async def ask(client, question, model, history=(), today=None):
    """One question, answered through an open MCP client."""
    today = today or date.today()
    listed = await client.list_tools()
    tools = [_spec(tool) for tool in listed.tools]
    messages = [{'role': 'system',
                 'content': f'{SYSTEM} Today is {today.isoformat()}.'},
                *history,
                {'role': 'user', 'content': question}]
    calls = []
    for _ in range(MOST_ROUNDS):
        reply = model(messages, tools)
        requests = reply.get('tool_calls') or []
        if not requests:
            text = (reply.get('content') or '').strip()
            if invented(text, [call.result for call in calls], question):
                return AgentAnswer(_fallback(calls), calls, rejected=True,
                                   draft=text)
            return AgentAnswer(text, calls, rejected=False, draft=text)
        messages.append(reply)
        for request in requests:
            call = await _call(client, request)
            calls.append(call)
            messages.append({'role': 'tool', 'tool_call_id': request['id'],
                             'content': call.result})
    return AgentAnswer(_fallback(calls), calls, rejected=True)


async def ask_server(target, question, model, history=(), today=None):
    """Open a client on a server, or on stdio parameters, and ask."""
    async with Client(target) as client:
        return await ask(client, question, model, history, today)
