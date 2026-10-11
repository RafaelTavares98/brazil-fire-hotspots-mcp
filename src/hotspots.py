"""INPE's daily fire file, read into hotspots.

INPE writes one row per detection, per satellite. The same fire seen by
three satellites is three rows, so a count of rows is not a count of
fires. INPE's own figures use one satellite only, and so does this.
"""

import csv
import io
from datetime import datetime, timezone

#: The satellite INPE counts with. One pass a day at the same hour, every
#: year since 2002, so this year compares with last year.
REFERENCE_SATELLITE = 'AQUA_M-T'

#: What INPE writes where it has no value.
UNKNOWN = -999

COLUMNS = {'id', 'lat', 'lon', 'data_hora_gmt', 'satelite', 'municipio',
           'estado', 'bioma', 'numero_dias_sem_chuva', 'precipitacao',
           'risco_fogo', 'frp'}

YEARLY_COLUMNS = {'foco_id', 'lat', 'lon', 'data_pas', 'estado',
                  'municipio', 'bioma'}


class NotAnInpeFile(Exception):
    """The text does not carry the columns INPE writes."""


class Hotspot:
    """One detection of heat, by one satellite, at one moment."""

    def __init__(self, detection_id, latitude, longitude, seen_at,
                 satellite, city, state, biome, dry_days, rain_mm,
                 fire_risk, power_mw):
        self.detection_id = detection_id
        self.latitude = latitude
        self.longitude = longitude
        self.seen_at = seen_at
        self.satellite = satellite
        self.city = city
        self.state = state
        self.biome = biome
        self.dry_days = dry_days
        self.rain_mm = rain_mm
        self.fire_risk = fire_risk
        self.power_mw = power_mw


def _measure(text):
    """A number, or None where INPE has none."""
    text = text.strip()
    if not text:
        return None
    value = float(text)
    return None if value == UNKNOWN else value


def _days(text):
    value = _measure(text)
    return None if value is None else int(value)


def _moment(text):
    stamp = datetime.strptime(text.strip(), '%Y-%m-%d %H:%M:%S')
    return stamp.replace(tzinfo=timezone.utc)


def _hotspot(row):
    return Hotspot(
        detection_id=row['id'],
        latitude=float(row['lat']),
        longitude=float(row['lon']),
        seen_at=_moment(row['data_hora_gmt']),
        satellite=row['satelite'],
        city=row['municipio'],
        state=row['estado'],
        biome=row['bioma'],
        dry_days=_days(row['numero_dias_sem_chuva']),
        rain_mm=_measure(row['precipitacao']),
        fire_risk=_measure(row['risco_fogo']),
        power_mw=_measure(row['frp']),
    )


def _yearly_hotspot(row):
    """The yearly file is the reference satellite only, with no weather."""
    return Hotspot(
        detection_id=row['foco_id'],
        latitude=float(row['lat']),
        longitude=float(row['lon']),
        seen_at=_moment(row['data_pas']),
        satellite=REFERENCE_SATELLITE,
        city=row['municipio'],
        state=row['estado'],
        biome=row['bioma'],
        dry_days=None,
        rain_mm=None,
        fire_risk=None,
        power_mw=None,
    )


def _rows(text, columns):
    """The rows of text, once it is known to carry these columns."""
    rows = csv.DictReader(io.StringIO(text))
    missing = columns - set(rows.fieldnames or [])
    if missing:
        raise NotAnInpeFile(f'missing columns: {sorted(missing)}')
    return rows


def read(text):
    """Every row of one daily or monthly file. Nothing is dropped here."""
    return [_hotspot(row) for row in _rows(text, COLUMNS)]


def read_yearly(text):
    """Every row of one yearly reference file, as the same hotspots."""
    return [_yearly_hotspot(row) for row in _rows(text, YEARLY_COLUMNS)]


def reference_only(spots):
    """One point per fire: the reference satellite, each detection once."""
    seen = set()
    counted = []
    for spot in spots:
        if spot.satellite != REFERENCE_SATELLITE:
            continue
        if spot.detection_id in seen:
            continue
        seen.add(spot.detection_id)
        counted.append(spot)
    return counted
