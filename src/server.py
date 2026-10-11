"""The MCP server: six read-only tools over the fire store.

Each tool is a thin door onto one function in questions.py. Here the
text a model sends becomes dates and numbers, and the answer becomes
JSON. Anything refused below is handed back as a sentence the model can
read and act on, never as a zero.
"""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import provenance
import questions
import replies

#: Every tool only reads, so a client may run them without asking.
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

INSTRUCTIONS = (
    'Fire hotspots detected over Brazil by INPE, counted the way INPE '
    'counts them: one reference satellite, one point per fire, from 2003 '
    'to yesterday. Dates are YYYY-MM-DD. A state may be its name or its '
    'two-letter code. Every number comes from the database; quote it, do '
    'not estimate.')

_day = replies.day


def _reply(database, ask):
    """The shared answer; a refusal becomes an error the model reads."""
    try:
        return replies.reply(database, ask)
    except replies.Refused as refused:
        raise ToolError(str(refused)) from refused


def build(database):
    """A server answering from one open store."""
    app = MCPServer('fire-mcp', instructions=INSTRUCTIONS)

    @app.resource('fires://about', mime_type='text/markdown')
    def about() -> str:
        """What a hotspot is and is not, and how to quote a number."""
        return provenance.ABOUT

    @app.tool(annotations=READ_ONLY)
    def count_fires(state: str | None = None, city: str | None = None,
                    biome: str | None = None, since: str | None = None,
                    until: str | None = None) -> dict:
        """How many fires INPE detected, optionally within one state, city
        or biome, and between two dates (both included). Use this for any
        "how many" question."""
        return _reply(database, lambda: questions.count(
            database, state=state, city=city, biome=biome,
            since=_day(since), until=_day(until)))

    @app.tool(annotations=READ_ONLY)
    def top_cities(limit: int = 10, state: str | None = None,
                   biome: str | None = None, since: str | None = None,
                   until: str | None = None) -> dict:
        """The cities with the most fires, biggest first, as
        [city, state, fires]. Use this for "where did it burn most"."""
        return _reply(database, lambda: questions.top_cities(
            database, limit=limit, state=state, biome=biome,
            since=_day(since), until=_day(until)))

    @app.tool(annotations=READ_ONLY)
    def daily_series(since: str, until: str, state: str | None = None,
                     city: str | None = None,
                     biome: str | None = None) -> dict:
        """Fires per day between two dates, quiet days as zero, at most
        731 days. Use this to draw a line over time."""
        return _reply(database, lambda: questions.daily_series(
            database, since=_day(since), until=_day(until), state=state,
            city=city, biome=biome))

    @app.tool(annotations=READ_ONLY)
    def compare_periods(first_since: str, first_until: str,
                        second_since: str, second_until: str,
                        state: str | None = None, city: str | None = None,
                        biome: str | None = None) -> dict:
        """The fire count over two periods with the same filters, and the
        change between them. change_percent is null when the first period
        had no fires. Use this for "more or less than last year"."""
        return _reply(database, lambda: questions.compare(
            database,
            first=(_day(first_since), _day(first_until)),
            second=(_day(second_since), _day(second_until)),
            state=state, city=city, biome=biome))

    @app.tool(annotations=READ_ONLY)
    def fires_near(latitude: float, longitude: float, km: float,
                   since: str | None = None,
                   until: str | None = None) -> dict:
        """How many fires lie within km (at most 500) of a point given in
        decimal degrees. Use this for a farm, a town or a park."""
        return _reply(database, lambda: questions.near(
            database, latitude=latitude, longitude=longitude, km=km,
            since=_day(since), until=_day(until)))

    @app.tool(annotations=READ_ONLY)
    def fire_points(state: str | None = None, city: str | None = None,
                    biome: str | None = None, since: str | None = None,
                    until: str | None = None, limit: int = 5000) -> dict:
        """The fires as a GeoJSON layer for a map, newest first, at most
        5000. "total" is the full count; "truncated" says the layer was
        cut."""
        return _reply(database, lambda: questions.points(
            database, limit=limit, state=state, city=city, biome=biome,
            since=_day(since), until=_day(until)))

    return app
