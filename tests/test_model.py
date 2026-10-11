"""The DeepSeek client, against a fake transport. No network, no key."""

import json

import httpx
import pytest

import model


def transport(reply, seen):
    def handle(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=reply)
    return httpx.MockTransport(handle)


REPLY = {'choices': [{'message': {'role': 'assistant', 'content': 'Hi.'}}]}


class TestAsking:
    def test_the_message_comes_back(self):
        seen = []
        ask = model.deepseek('key', transport=transport(REPLY, seen))

        assert ask([{'role': 'user', 'content': 'hi'}], []) == {
            'role': 'assistant', 'content': 'Hi.'}

    def test_tools_and_messages_are_sent(self):
        seen = []
        ask = model.deepseek('key', transport=transport(REPLY, seen))
        tools = [{'type': 'function', 'function': {'name': 'count_fires'}}]

        ask([{'role': 'user', 'content': 'hi'}], tools)

        assert seen[0]['tools'] == tools
        assert seen[0]['model'] == model.MODEL
        assert seen[0]['temperature'] == 0

    def test_no_tools_sends_no_tool_list(self):
        """An empty tool list is refused by the API."""
        seen = []
        ask = model.deepseek('key', transport=transport(REPLY, seen))

        ask([{'role': 'user', 'content': 'hi'}], [])

        assert 'tools' not in seen[0]

    def test_a_failed_call_is_said_plainly(self):
        def handle(request):
            return httpx.Response(401, json={'error': 'bad key'})
        ask = model.deepseek('key', transport=httpx.MockTransport(handle))

        with pytest.raises(model.ModelFailed):
            ask([{'role': 'user', 'content': 'hi'}], [])


class TestTheKey:
    def test_the_environment_comes_first(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'from-env')

        assert model.key() == 'from-env'

    def test_no_key_anywhere_is_none(self, monkeypatch):
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring', lambda: None)

        assert model.key() is None
