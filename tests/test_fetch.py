"""Bringing INPE's files into the store.

History comes from the yearly files, which hold the reference satellite
only. The current year comes from the monthly files, which hold every
satellite and are cut down to the reference one here. No test touches
the network: a fake server answers instead.
"""

import io
import zipfile
from datetime import date

import pytest

import fetch
import store


class FakeServer:
    """Answers each URL with the bytes a test gave it, and 404 otherwise."""

    def __init__(self, pages):
        self.pages = pages
        self.asked = []

    def __call__(self, url):
        self.asked.append(url)
        if url not in self.pages:
            return 404, b''
        return 200, self.pages[url]


def zipped(name, text):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


@pytest.fixture
def database(tmp_path):
    return store.open_store(tmp_path / 'fires.duckdb')


@pytest.fixture
def yearly_text():
    from conftest import HERE
    return (HERE / 'tests' / 'fixtures' / 'focos_yearly_sample.csv'
            ).read_text(encoding='utf-8')


class TestAddresses:
    def test_a_year_lives_in_the_reference_folder(self):
        assert fetch.yearly_url(2025) == (
            'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/'
            'csv/anual/Brasil_sat_ref/focos_br_ref_2025.zip')

    def test_a_month_lives_in_the_monthly_folder(self):
        assert fetch.monthly_url(2026, 9) == (
            'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/'
            'csv/mensal/Brasil/focos_mensal_br_202609.csv')


class TestLoadingAYear:
    def test_the_zip_is_opened_and_saved(self, database, yearly_text):
        server = FakeServer({fetch.yearly_url(2025):
                             zipped('tmp/focos_br_ref_2025.csv',
                                    yearly_text)})

        assert fetch.load_year(database, 2025, get=server) == 3
        assert store.size(database) == 3

    def test_a_missing_year_is_said_plainly(self, database):
        with pytest.raises(fetch.NotPublished):
            fetch.load_year(database, 1990, get=FakeServer({}))


class TestLoadingAMonth:
    def test_only_the_reference_satellite_is_kept(self, database,
                                                  sample_text):
        server = FakeServer({fetch.monthly_url(2026, 10):
                             sample_text.encode('utf-8')})

        assert fetch.load_month(database, 2026, 10, get=server) == 4

    def test_loading_a_month_twice_adds_nothing(self, database,
                                                sample_text):
        server = FakeServer({fetch.monthly_url(2026, 10):
                             sample_text.encode('utf-8')})
        fetch.load_month(database, 2026, 10, get=server)

        assert fetch.load_month(database, 2026, 10, get=server) == 0


class TestWhatToLoad:
    def test_past_years_come_whole_and_this_year_by_month(self):
        """The yearly file for the current year does not exist yet."""
        plan = fetch.plan(first_year=2024, today=date(2026, 3, 15))

        assert plan == [('year', 2024), ('year', 2025),
                        ('month', 2026, 1), ('month', 2026, 2),
                        ('month', 2026, 3)]
