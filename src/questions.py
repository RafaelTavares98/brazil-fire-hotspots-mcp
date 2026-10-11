"""The questions the MCP tools answer, each one a single SQL query.

Every number in every answer comes out of the store. Nothing here guesses,
rounds for show, or fills a gap: a place that is not known is refused, a
quiet day is a zero, and a cut list says it was cut.
"""

from datetime import date, timedelta

import places

#: The longest daily series one answer carries. Longer is a file.
MOST_DAYS = 731

#: The widest circle a "near" question may draw, in kilometres.
WIDEST_KM = 500

#: The most points one map answer carries.
MOST_POINTS = 5000


class BadPeriod(Exception):
    """A period that ends before it starts, is missing, or is too long."""


class BadRadius(Exception):
    """A circle too large to mean "near"."""


class Answer:
    """A value, and the filters that produced it."""

    def __init__(self, value, filters):
        self.value = value
        self.filters = filters


def _check_period(since, until):
    if since and until and until < since:
        raise BadPeriod(f'the period ends ({until}) before it starts '
                        f'({since})')


def _where(state=None, city=None, biome=None, since=None, until=None):
    """The WHERE clause, its parameters, and the filters as understood."""
    _check_period(since, until)
    clauses, values, understood = ['TRUE'], [], {}
    if state:
        understood['state'] = places.state(state)
        clauses.append('state = ?')
        values.append(understood['state'])
    if city:
        understood['city'] = city.strip().upper()
        clauses.append('strip_accents(lower(city)) = ?')
        values.append(places.plain(city))
    if biome:
        understood['biome'] = places.biome(biome)
        clauses.append('biome = ?')
        values.append(understood['biome'])
    if since:
        understood['since'] = since.isoformat()
        clauses.append('seen_at >= ?')
        values.append(since)
    if until:
        understood['until'] = until.isoformat()
        clauses.append('seen_at < ?')
        values.append(until + timedelta(days=1))
    return ' AND '.join(clauses), values, understood


def count(database, **filters):
    """How many fires match the filters."""
    where, values, understood = _where(**filters)
    found = database.execute(
        f'SELECT count(*) FROM hotspots WHERE {where}', values).fetchone()[0]
    return Answer(found, understood)


def top_cities(database, limit=10, **filters):
    """The cities with the most fires, biggest first, ties by name."""
    where, values, understood = _where(**filters)
    rows = database.execute(
        f'SELECT city, state, count(*) AS fires FROM hotspots '
        f'WHERE {where} GROUP BY city, state '
        f'ORDER BY fires DESC, city LIMIT ?', values + [limit]).fetchall()
    return Answer([tuple(row) for row in rows], understood)


def daily_series(database, since=None, until=None, **filters):
    """Fires per day, with the quiet days as zeros."""
    if not since or not until:
        raise BadPeriod('a daily series needs both since and until')
    if (until - since).days + 1 > MOST_DAYS:
        raise BadPeriod(f'a daily series covers at most {MOST_DAYS} days')
    where, values, understood = _where(since=since, until=until, **filters)
    rows = dict(database.execute(
        f'SELECT seen_at::DATE, count(*) FROM hotspots WHERE {where} '
        f'GROUP BY 1', values).fetchall())
    days = [since + timedelta(days=n)
            for n in range((until - since).days + 1)]
    return Answer([(day, rows.get(day, 0)) for day in days], understood)


def compare(database, first, second, **filters):
    """The same filters over two periods, and the change between them."""
    before = count(database, since=first[0], until=first[1], **filters)
    after = count(database, since=second[0], until=second[1], **filters)
    change = after.value - before.value
    percent = None
    if before.value:
        percent = round(100 * change / before.value, 1)
    understood = dict(before.filters)
    understood.pop('since', None)
    understood.pop('until', None)
    understood['first'] = [first[0].isoformat(), first[1].isoformat()]
    understood['second'] = [second[0].isoformat(), second[1].isoformat()]
    return Answer({'first': before.value, 'second': after.value,
                   'change': change, 'change_percent': percent}, understood)


def near(database, latitude, longitude, km, **filters):
    """How many fires lie within km of a point, on the Earth's surface."""
    if not 0 < km <= WIDEST_KM:
        raise BadRadius(f'the radius must be above 0 and at most '
                        f'{WIDEST_KM} km')
    where, values, understood = _where(**filters)
    found = database.execute(
        f'SELECT count(*) FROM hotspots WHERE {where} AND '
        f'2 * 6371 * asin(sqrt('
        f'pow(sin(radians(latitude - ?) / 2), 2) + '
        f'cos(radians(?)) * cos(radians(latitude)) * '
        f'pow(sin(radians(longitude - ?) / 2), 2))) <= ?',
        values + [latitude, latitude, longitude, km]).fetchone()[0]
    understood.update(latitude=latitude, longitude=longitude, km=km)
    return Answer(found, understood)


def points(database, limit=MOST_POINTS, **filters):
    """The fires as a GeoJSON map layer, cut at limit and saying so."""
    where, values, understood = _where(**filters)
    total = count(database, **filters).value
    rows = database.execute(
        f'SELECT longitude, latitude, seen_at, city, state FROM hotspots '
        f'WHERE {where} ORDER BY seen_at DESC LIMIT ?',
        values + [min(limit, MOST_POINTS)]).fetchall()
    features = [{
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
        'properties': {'seen_at': seen.isoformat(), 'city': city,
                       'state': state},
    } for lon, lat, seen, city, state in rows]
    return Answer({'type': 'FeatureCollection', 'features': features,
                   'total': total, 'truncated': total > len(features)},
                  understood)
