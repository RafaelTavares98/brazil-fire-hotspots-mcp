"""The MCP server, spoken to the way an AI assistant speaks to it.

A real MCP client talks to the server in memory: it lists the tools,
calls them with plain JSON, and reads back what a model would read. The
same seven fires as in test_questions.
"""

import asyncio
import json

import pytest
from mcp.client.client import Client

import hotspots
import server
import store

TOOLS = {'count_fires', 'top_cities', 'daily_series', 'compare_periods',
         'fires_near', 'fire_points'}


@pytest.fixture
def mcp_server(tmp_path, sample, yearly):
    held = store.open_store(tmp_path / 'fires.duckdb')
    store.save(held, hotspots.reference_only(sample) + yearly)
    return server.build(held)


def ask(mcp_server, call):
    async def talk():
        async with Client(mcp_server) as client:
            return await call(client)
    return asyncio.run(talk())


def call_tool(mcp_server, name, arguments):
    result = ask(mcp_server, lambda client: client.call_tool(name, arguments))
    return result.is_error, json.loads(result.content[0].text) \
        if not result.is_error else result.content[0].text


class TestTheMenu:
    def test_the_six_tools_are_offered(self, mcp_server):
        listed = ask(mcp_server, lambda client: client.list_tools())

        assert {tool.name for tool in listed.tools} == TOOLS

    def test_every_tool_explains_itself(self, mcp_server):
        """The description is all a model reads before choosing."""
        listed = ask(mcp_server, lambda client: client.list_tools())

        for tool in listed.tools:
            assert len(tool.description) > 60, tool.name

    def test_every_tool_only_reads(self, mcp_server):
        """A client may run read-only tools without asking each time."""
        listed = ask(mcp_server, lambda client: client.list_tools())

        for tool in listed.tools:
            assert tool.annotations.read_only_hint is True, tool.name


class TestCalling:
    def test_a_count_comes_back_with_its_filters(self, mcp_server):
        failed, answer = call_tool(mcp_server, 'count_fires',
                                   {'state': 'go', 'since': '2026-01-01'})

        assert not failed
        assert answer['value'] == 3
        assert answer['filters']['state'] == 'GOIÁS'

    def test_dates_travel_as_text(self, mcp_server):
        failed, answer = call_tool(
            mcp_server, 'daily_series',
            {'since': '2025-09-10', 'until': '2025-09-11'})

        assert not failed
        assert answer['value'] == [['2025-09-10', 1], ['2025-09-11', 1]]

    def test_compare_takes_two_periods(self, mcp_server):
        failed, answer = call_tool(mcp_server, 'compare_periods', {
            'state': 'GO',
            'first_since': '2025-09-01', 'first_until': '2025-09-30',
            'second_since': '2026-10-01', 'second_until': '2026-10-31'})

        assert not failed
        assert answer['value']['change_percent'] == 50.0

    def test_near_counts_in_a_circle(self, mcp_server):
        failed, answer = call_tool(mcp_server, 'fires_near', {
            'latitude': -16.1, 'longitude': -49.2, 'km': 20,
            'since': '2026-10-01'})

        assert not failed
        assert answer['value'] == 2


class TestTrust:
    def test_every_answer_carries_its_provenance(self, mcp_server):
        failed, answer = call_tool(mcp_server, 'count_fires',
                                   {'state': 'GO'})

        assert not failed
        assert answer['provenance']['satellite'] == 'AQUA_M-T'
        assert answer['provenance']['held'] == ['2025-01-01',
                                                '2026-10-02']

    def test_a_period_past_the_data_warns(self, mcp_server):
        failed, answer = call_tool(mcp_server, 'count_fires',
                                   {'since': '2026-10-01',
                                    'until': '2026-12-31'})

        assert not failed
        assert answer['provenance']['warnings']

    def test_the_caveats_are_a_resource(self, mcp_server):
        """A model can read the limits of the data before it answers."""
        listed = ask(mcp_server, lambda client: client.list_resources())

        assert 'fires://about' in {str(r.uri) for r in listed.resources}


class TestRefusing:
    def test_an_unknown_state_is_an_error_the_model_can_read(
            self, mcp_server):
        """Not a crash, and not a zero: a sentence that says what went
        wrong, so the model can ask again."""
        failed, message = call_tool(mcp_server, 'count_fires',
                                    {'state': 'Goiaz'})

        assert failed
        assert 'GOIÁS' in message

    def test_a_date_that_is_not_a_date_is_refused(self, mcp_server):
        failed, message = call_tool(mcp_server, 'count_fires',
                                    {'since': 'last week'})

        assert failed
        assert 'YYYY-MM-DD' in message
