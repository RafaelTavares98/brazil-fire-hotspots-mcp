"""Keeping hotspots in one DuckDB file.

The file is the whole database: no server, no password. Loading the same
day twice must not count its fires twice, because a daily job that ran
twice is an ordinary day, not an error.
"""

from datetime import datetime, timezone

import pytest

import hotspots
import store


@pytest.fixture
def database(tmp_path):
    return store.open_store(tmp_path / 'fires.duckdb')


@pytest.fixture
def counted(sample):
    return hotspots.reference_only(sample)


class TestSaving:
    def test_a_new_store_is_empty(self, database):
        assert store.size(database) == 0

    def test_saved_hotspots_are_kept(self, database, counted):
        store.save(database, counted)

        assert store.size(database) == 4

    def test_saving_reports_how_many_were_new(self, database, counted):
        assert store.save(database, counted) == 4

    def test_saving_the_same_day_twice_adds_nothing(self, database,
                                                    counted):
        store.save(database, counted)

        assert store.save(database, counted) == 0
        assert store.size(database) == 4

    def test_a_repeat_inside_one_batch_is_kept_once(self, database,
                                                     sample):
        """INPE's file repeats a row now and then. The batch must not
        fail on it, and must not keep it twice."""
        store.save(database, sample)

        assert store.size(database) == 7

    def test_saving_nothing_is_allowed(self, database):
        assert store.save(database, []) == 0

    def test_the_file_survives_closing(self, tmp_path, counted):
        """The point of a file is that tomorrow it is still there."""
        path = tmp_path / 'fires.duckdb'
        first = store.open_store(path)
        store.save(first, counted)
        first.close()

        assert store.size(store.open_store(path)) == 4


class TestWhatComesBack:
    def test_a_hotspot_comes_back_as_it_went_in(self, database, counted):
        store.save(database, counted)

        back = store.by_id(database, 'a1')

        assert back.city == 'NIQUELÂNDIA'
        assert back.latitude == pytest.approx(-16.1)
        assert back.dry_days == 12
        assert back.seen_at == datetime(2026, 10, 1, 17, 5,
                                        tzinfo=timezone.utc)

    def test_unknown_stays_unknown(self, database, counted):
        """None in, None out. A zero would be a measurement nobody
        made."""
        store.save(database, counted)

        back = store.by_id(database, 'a2')

        assert back.fire_risk is None
        assert back.power_mw is None

    def test_an_id_not_on_file_is_refused(self, database):
        with pytest.raises(store.NotOnFile):
            store.by_id(database, 'nope')


class TestCoverage:
    def test_it_knows_which_days_it_holds(self, database, counted):
        """A count over days never loaded is not zero fires. The tools
        need to know the difference."""
        store.save(database, counted)

        first, last = store.days_held(database)

        assert first.isoformat() == '2026-10-01'
        assert last.isoformat() == '2026-10-02'

    def test_an_empty_store_holds_no_days(self, database):
        assert store.days_held(database) == (None, None)
