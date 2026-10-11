"""Where every answer came from, and what it does not cover.

A count over days the store never loaded looks exactly like a quiet
week. The answer has to say which days it really covers, which satellite
counted, and where the data came from, so the reader can check it.

The store here holds 2025-01-01 to 2026-10-02.
"""

from datetime import date

import pytest

import hotspots
import provenance
import store


@pytest.fixture
def database(tmp_path, sample, yearly):
    held = store.open_store(tmp_path / 'fires.duckdb')
    store.save(held, hotspots.reference_only(sample) + yearly)
    return held


class TestSource:
    def test_it_names_inpe_and_the_satellite(self, database):
        about = provenance.describe(database)

        assert about['source'] == 'INPE, Programa Queimadas'
        assert about['satellite'] == 'AQUA_M-T'
        assert about['source_url'].startswith('https://')

    def test_it_says_which_days_are_held(self, database):
        about = provenance.describe(database)

        assert about['held'] == ['2025-01-01', '2026-10-02']


class TestCoverage:
    def test_a_period_inside_the_data_has_no_warning(self, database):
        about = provenance.describe(database, since=date(2025, 3, 1),
                                    until=date(2025, 9, 1))

        assert about['warnings'] == []

    def test_a_period_ending_after_the_data_is_flagged(self, database):
        """Asking about this week, before tonight's load, must not read
        as a quiet week."""
        about = provenance.describe(database, since=date(2026, 10, 1),
                                    until=date(2026, 10, 31))

        assert about['warnings'] == [
            'The data ends on 2026-10-02. Days after it are not counted '
            'yet.']

    def test_a_period_starting_before_the_data_is_flagged(self, database):
        about = provenance.describe(database, since=date(2020, 1, 1),
                                    until=date(2025, 6, 1))

        assert about['warnings'] == [
            'The data starts on 2025-01-01. Days before it are not '
            'counted.']

    def test_no_period_means_everything_held(self, database):
        assert provenance.describe(database)['warnings'] == []

    def test_an_empty_store_says_so(self, tmp_path):
        empty = store.open_store(tmp_path / 'empty.duckdb')

        about = provenance.describe(empty)

        assert about['held'] is None
        assert about['warnings'] == ['The store is empty. Run load.py.']


class TestCaveats:
    def test_the_limits_of_a_hotspot_are_written_down(self):
        """What the papers on this data repeat: a hotspot is not a fire's
        size, and small fires are missed."""
        text = provenance.ABOUT

        assert 'not the area burned' in text
        assert 'small' in text
        assert 'AQUA_M-T' in text
