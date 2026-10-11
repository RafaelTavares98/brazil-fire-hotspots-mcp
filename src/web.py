"""The web API the panel will read. JSON only, no page yet.

Every route answers through replies.reply, the same function the MCP
tools use, so a number on the map and a number in the chat cannot
disagree. /api/ask runs the agent against the MCP server in memory: the
chat uses exactly the tools any other assistant would.
"""

import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import agent
import provenance
import questions
import replies
import server

day = replies.day


class Question(BaseModel):
    question: str
    history: list[dict] = []


def _answer(database, ask):
    try:
        return replies.reply(database, ask)
    except replies.Refused as refused:
        raise HTTPException(400, str(refused)) from refused


def _plain_turns(history):
    """User and assistant text only, the last six turns. A page must not
    be able to send a system turn and rewrite the rules."""
    turns = [{'role': turn['role'], 'content': turn['content']}
             for turn in history
             if turn.get('role') in ('user', 'assistant')
             and isinstance(turn.get('content'), str)]
    return turns[-6:]


def _call(call):
    """One tool call, with its result as JSON when it succeeded."""
    result = call.result if call.failed else json.loads(call.result)
    return {'name': call.name, 'arguments': call.arguments,
            'failed': call.failed, 'result': result}


def create(database, model):
    """The API over one open store. model may be None: then /api/ask
    says why it cannot answer, and everything else still works."""
    app = FastAPI(title='Fire MCP API')
    tools = server.build(database)

    @app.get('/api/health')
    def health():
        about = provenance.describe(database)
        return {'held': about['held'], 'model_connected': model is not None}

    @app.get('/api/count')
    def count(state: str | None = None, city: str | None = None,
              biome: str | None = None, since: str | None = None,
              until: str | None = None):
        return _answer(database, lambda: questions.count(
            database, state=state, city=city, biome=biome,
            since=day(since), until=day(until)))

    @app.get('/api/top-cities')
    def top_cities(limit: int = 10, state: str | None = None,
                   biome: str | None = None, since: str | None = None,
                   until: str | None = None):
        return _answer(database, lambda: questions.top_cities(
            database, limit=limit, state=state, biome=biome,
            since=day(since), until=day(until)))

    @app.get('/api/series')
    def series(since: str, until: str, state: str | None = None,
               city: str | None = None, biome: str | None = None):
        return _answer(database, lambda: questions.daily_series(
            database, since=day(since), until=day(until), state=state,
            city=city, biome=biome))

    @app.get('/api/compare')
    def compare(first_since: str, first_until: str, second_since: str,
                second_until: str, state: str | None = None,
                city: str | None = None, biome: str | None = None):
        return _answer(database, lambda: questions.compare(
            database, first=(day(first_since), day(first_until)),
            second=(day(second_since), day(second_until)),
            state=state, city=city, biome=biome))

    @app.get('/api/near')
    def near(latitude: float, longitude: float, km: float,
             since: str | None = None, until: str | None = None):
        return _answer(database, lambda: questions.near(
            database, latitude=latitude, longitude=longitude, km=km,
            since=day(since), until=day(until)))

    @app.get('/api/points')
    def points(state: str | None = None, city: str | None = None,
               biome: str | None = None, since: str | None = None,
               until: str | None = None, limit: int = 5000):
        return _answer(database, lambda: questions.points(
            database, limit=limit, state=state, city=city, biome=biome,
            since=day(since), until=day(until)))

    @app.post('/api/ask')
    async def ask(body: Question):
        if not body.question.strip():
            raise HTTPException(400, 'the question is empty')
        if model is None:
            raise HTTPException(503, 'No model is connected. Set '
                                     'DEEPSEEK_API_KEY or store the key '
                                     'in the keyring under fire-mcp.')
        found = await agent.ask_server(tools, body.question, model,
                                       history=_plain_turns(body.history))
        return {'text': found.text, 'rejected': found.rejected,
                'calls': [_call(call) for call in found.calls]}

    return app
