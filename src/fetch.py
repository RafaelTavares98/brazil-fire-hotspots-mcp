"""INPE's files, brought into the store.

History comes from the yearly files, which hold the reference satellite
only. The current year has no yearly file yet, so it comes from the
monthly ones, which hold every satellite and are cut down here.
"""

import io
import zipfile

import httpx

import hotspots
import store

BASE = 'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv'


class NotPublished(Exception):
    """INPE has no file at that address."""


def yearly_url(year):
    return f'{BASE}/anual/Brasil_sat_ref/focos_br_ref_{year}.zip'


def monthly_url(year, month):
    return f'{BASE}/mensal/Brasil/focos_mensal_br_{year}{month:02d}.csv'


def web_get(url):
    """The real server: status and bytes, the shape the fakes answer in."""
    reply = httpx.get(url, timeout=300)
    return reply.status_code, reply.content


def _download(url, get):
    status, body = get(url)
    if status != 200:
        raise NotPublished(f'{url} answered {status}')
    return body


def _unzip(body):
    """The one CSV inside a yearly zip, as text."""
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        name = next(n for n in archive.namelist() if n.endswith('.csv'))
        return archive.read(name).decode('utf-8')


def load_year(database, year, get=web_get):
    """Save one past year. Returns how many hotspots were new."""
    text = _unzip(_download(yearly_url(year), get))
    return store.save(database, hotspots.read_yearly(text))


def load_month(database, year, month, get=web_get):
    """Save one month of the current year, reference satellite only."""
    text = _download(monthly_url(year, month), get).decode('utf-8')
    return store.save(database,
                      hotspots.reference_only(hotspots.read(text)))


def plan(first_year, today):
    """Every file to load, oldest first: whole past years, then months."""
    steps = [('year', year) for year in range(first_year, today.year)]
    steps += [('month', today.year, month)
              for month in range(1, today.month + 1)]
    return steps
