"""The agent: a model that answers by calling the MCP tools.

The model picks tools and writes the sentence. It never produces a
number of its own: every number in the sentence must appear in what the
tools answered, or the sentence is thrown away. A fake model plays the
part here, saying exactly what each test scripts.
"""

import asyncio
import json

import pytest

import agent
import hotspots
import server
import store


class FakeModel:
    """Replies with scripted messages, and records what it was shown."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.seen = []

    def __call__(self, messages, tools):
        self.seen.append((list(messages), tools))
        if not self.replies:
            raise AssertionError('the model was asked more times than '
                                 'the test expected')
        return self.replies.pop(0)


def calls(name, arguments):
    return {'role': 'assistant', 'content': None, 'tool_calls': [{
        'id': 'call-1', 'type': 'function',
        'function': {'name': name, 'arguments': json.dumps(arguments)}}]}


def says(text):
    return {'role': 'assistant', 'content': text}


@pytest.fixture
def mcp_server(tmp_path, sample, yearly):
    held = store.open_store(tmp_path / 'fires.duckdb')
    store.save(held, hotspots.reference_only(sample) + yearly)
    return server.build(held)


def answer(mcp_server, question, model):
    return asyncio.run(agent.ask_server(mcp_server, question, model))


class TestAnswering:
    def test_a_tool_is_called_and_its_number_is_said(self, mcp_server):
        model = FakeModel(calls('count_fires', {'state': 'GO'}),
                          says('INPE counted 5 fires in Goiás.'))

        found = answer(mcp_server, 'How many fires in Goiás?', model)

        assert found.text == 'INPE counted 5 fires in Goiás.'
        assert found.rejected is False
        assert [call.name for call in found.calls] == ['count_fires']

    def test_the_model_is_shown_the_six_tools(self, mcp_server):
        model = FakeModel(says('Ask me about fires in Brazil.'))

        answer(mcp_server, 'hello', model)

        _, tools = model.seen[0]
        assert len(tools) == 6
        assert tools[0]['type'] == 'function'

    def test_the_model_is_told_what_day_it_is(self, mcp_server):
        """"This year so far" means nothing to a model that does not
        know the date."""
        from datetime import date
        model = FakeModel(says('Hello.'))

        asyncio.run(agent.ask_server(mcp_server, 'hi', model,
                                     today=date(2026, 10, 11)))

        messages, _ = model.seen[0]
        assert '2026-10-11' in messages[0]['content']

    def test_the_tool_result_goes_back_to_the_model(self, mcp_server):
        model = FakeModel(calls('count_fires', {'state': 'GO'}),
                          says('There were 5.'))

        answer(mcp_server, 'How many in Goiás?', model)

        messages, _ = model.seen[1]
        assert messages[-1]['role'] == 'tool'
        assert json.loads(messages[-1]['content'])['value'] == 5


class TestTheNumberGuard:
    def test_an_invented_number_throws_the_sentence_away(self,
                                                         mcp_server):
        """The tool said 5. A model that writes 50 is not trusted."""
        model = FakeModel(calls('count_fires', {'state': 'GO'}),
                          says('INPE counted 50 fires in Goiás.'))

        found = answer(mcp_server, 'How many fires in Goiás?', model)

        assert found.rejected is True
        assert '50' not in found.text
        assert '5' in found.text

    def test_a_number_with_a_thousands_comma_is_the_same(self):
        assert agent.invented('There were 278,299 fires.',
                              ['{"value": 278299}']) == []

    def test_brazilian_thousands_are_the_same_number(self):
        """In Portuguese, 1.625 is one thousand six hundred and
        twenty-five."""
        assert agent.invented('Foram 1.625 focos.',
                              ['{"value": 1625}']) == []

    def test_a_brazilian_decimal_comma_is_the_same_number(self):
        assert agent.invented('Queda de 73,5%.',
                              ['{"change_percent": -73.5}']) == []

    def test_a_minus_sign_dropped_in_words_is_allowed(self):
        """"A fall of 73.5%" carries the sign in the word."""
        assert agent.invented('A fall of 73.5%.',
                              ['{"change_percent": -73.5}']) == []

    def test_the_draft_is_kept_when_rejected(self, mcp_server):
        """Whoever reads the log needs to see what was thrown away."""
        model = FakeModel(calls('count_fires', {'state': 'GO'}),
                          says('INPE counted 50 fires.'))

        found = answer(mcp_server, 'How many fires in Goiás?', model)

        assert found.draft == 'INPE counted 50 fires.'

    def test_a_number_from_the_question_is_allowed(self):
        """"In the last 30 days" is the reader's number, not an
        invention."""
        assert agent.invented('In the last 30 days: 4 fires.',
                              ['{"value": 4}'], question='last 30 days?'
                              ) == []

    def test_a_number_with_no_source_is_found(self):
        assert agent.invented('About 12 fires.', ['{"value": 4}']) == ['12']

    def test_a_number_said_without_any_tool_is_rejected(self,
                                                        mcp_server):
        model = FakeModel(says('Goiás had 431 fires in September.'))

        found = answer(mcp_server, 'Fires in Goiás in September?', model)

        assert found.rejected is True


class TestLimits:
    def test_a_refused_tool_call_reaches_the_model_as_text(self,
                                                           mcp_server):
        model = FakeModel(calls('count_fires', {'state': 'Goiaz'}),
                          calls('count_fires', {'state': 'GO'}),
                          says('There were 5.'))

        found = answer(mcp_server, 'Fires in Goiaz?', model)

        messages, _ = model.seen[1]
        assert 'GOIÁS' in messages[-1]['content']
        assert found.text == 'There were 5.'

    def test_the_loop_stops_after_a_few_rounds(self, mcp_server):
        """A model that keeps calling tools forever costs money and
        never answers."""
        model = FakeModel(*[calls('count_fires', {})] * agent.MOST_ROUNDS)

        found = answer(mcp_server, 'How many?', model)

        assert found.rejected is True
        assert len(model.seen) == agent.MOST_ROUNDS
