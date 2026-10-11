"""Hotspots kept in one DuckDB file.

The file is the whole database: no server, no password. A detection is
saved once, by its id, so loading the same day twice changes nothing.
"""

from datetime import timezone

import duckdb
import pandas

import hotspots

_TABLE = """
CREATE TABLE IF NOT EXISTS hotspots (
    detection_id VARCHAR PRIMARY KEY,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    seen_at TIMESTAMP NOT NULL,
    satellite VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    biome VARCHAR,
    dry_days INTEGER,
    rain_mm DOUBLE,
    fire_risk DOUBLE,
    power_mw DOUBLE
)
"""

#: The order every query reads and writes the columns in.
_COLUMNS = ('detection_id', 'latitude', 'longitude', 'seen_at', 'satellite',
            'city', 'state', 'biome', 'dry_days', 'rain_mm', 'fire_risk',
            'power_mw')


class NotOnFile(Exception):
    """No hotspot with that id was ever saved."""


def open_store(path):
    """The database at path, created on first use."""
    database = duckdb.connect(str(path))
    database.execute(_TABLE)
    return database


def size(database):
    return database.execute('SELECT count(*) FROM hotspots').fetchone()[0]


def _row(spot):
    """Times are stored as UTC without a zone, and given one back."""
    moment = spot.seen_at.astimezone(timezone.utc).replace(tzinfo=None)
    return (spot.detection_id, spot.latitude, spot.longitude, moment,
            spot.satellite, spot.city, spot.state, spot.biome,
            spot.dry_days, spot.rain_mm, spot.fire_risk, spot.power_mw)


def save(database, spots):
    """Keep the hotspots not already held. Returns how many were new.

    One insert for the whole batch. Row by row, a year of fires took
    longer than ten minutes.
    """
    rows = [_row(spot) for spot in spots]
    if not rows:
        return 0
    batch = pandas.DataFrame(rows, columns=_COLUMNS, dtype=object)
    before = size(database)
    database.register('batch', batch)
    database.execute(f'INSERT OR IGNORE INTO hotspots '
                     f'SELECT DISTINCT ON (detection_id) * FROM batch')
    database.unregister('batch')
    return size(database) - before


def _hotspot(row):
    values = dict(zip(_COLUMNS, row))
    values['seen_at'] = values['seen_at'].replace(tzinfo=timezone.utc)
    return hotspots.Hotspot(**values)


def by_id(database, detection_id):
    row = database.execute(
        f'SELECT {", ".join(_COLUMNS)} FROM hotspots '
        'WHERE detection_id = ?', [detection_id]).fetchone()
    if row is None:
        raise NotOnFile(detection_id)
    return _hotspot(row)


def days_held(database):
    """The first and last day on file, or (None, None) when empty."""
    return tuple(database.execute(
        'SELECT min(seen_at)::DATE, max(seen_at)::DATE FROM hotspots'
    ).fetchone())
