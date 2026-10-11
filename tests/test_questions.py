"""The questions the MCP tools answer, over a store small enough to check
by eye.

The store holds seven fires:

| id | day | state | city | biome |
|---|---|---|---|---|
| y1 | 2025-01-01 | PERNAMBUCO | SOLIDÃO | Caatinga |
| y2 | 2025-09-10 | GOIÁS | NIQUELÂNDIA | Cerrado |
| y3 | 2025-09-11 | GOIÁS | NIQUELÂNDIA | Cerrado |
| a1 | 2026-10-01 | GOIÁS | NIQUELÂNDIA | Cerrado |
| a2 | 2026-10-01 | GOIÁS | NIQUELÂNDIA | Cerrado |
| a3 | 2026-10-02 | GOIÁS | SÃO DOMINGOS | Cerrado |
| a4 | 2026-10-02 | PARÁ | ALTAMIRA | Amazônia |
"""

from datetime import date

import pytest

import hotspots
import questions
import store


@pytest.fixture
def database(tmp_path, sample, yearly):
    held = store.open_store(tmp_path / 'fires.duckdb')
    store.save(held, hotspots.reference_only(sample) + yearly)
    return held


class TestCount:
    def test_everything(self, database):
        assert questions.count(database).value == 7

    def test_one_state(self, database):
        assert questions.count(database, state='GO').value == 5

    def test_one_period(self, database):
        found = questions.count(database, since=date(2026, 10, 1),
                                until=date(2026, 10, 1))

        assert found.value == 2

    def test_the_period_includes_both_ends(self, database):
        found = questions.count(database, since=date(2025, 9, 10),
                                until=date(2025, 9, 11))

        assert found.value == 2

    def test_one_biome(self, database):
        assert questions.count(database, biome='amazonia').value == 1

    def test_one_city(self, database):
        found = questions.count(database, state='GO', city='são domingos')

        assert found.value == 1

    def test_filters_combine(self, database):
        found = questions.count(database, state='GO',
                                since=date(2026, 1, 1))

        assert found.value == 3

    def test_an_unknown_state_is_refused_not_zero(self, database):
        import places
        with pytest.raises(places.UnknownPlace):
            questions.count(database, state='Goiaz')

    def test_a_backwards_period_is_refused(self, database):
        with pytest.raises(questions.BadPeriod):
            questions.count(database, since=date(2026, 2, 1),
                            until=date(2026, 1, 1))


class TestTopCities:
    def test_ranked_biggest_first(self, database):
        found = questions.top_cities(database, limit=2)

        assert found.value == [('NIQUELÂNDIA', 'GOIÁS', 4),
                               ('ALTAMIRA', 'PARÁ', 1)]

    def test_a_tie_is_broken_by_name(self, database):
        """The same question must give the same list every time."""
        found = questions.top_cities(database, limit=4)

        assert [city for city, _, _ in found.value] == [
            'NIQUELÂNDIA', 'ALTAMIRA', 'SOLIDÃO', 'SÃO DOMINGOS']

    def test_within_a_state(self, database):
        found = questions.top_cities(database, state='GO')

        assert found.value == [('NIQUELÂNDIA', 'GOIÁS', 4),
                               ('SÃO DOMINGOS', 'GOIÁS', 1)]


class TestDailySeries:
    def test_a_day_without_fire_is_zero_not_missing(self, database):
        """A line with the quiet days left out draws a fire that never
        stopped."""
        found = questions.daily_series(database, since=date(2025, 9, 9),
                                       until=date(2025, 9, 12))

        assert found.value == [(date(2025, 9, 9), 0),
                               (date(2025, 9, 10), 1),
                               (date(2025, 9, 11), 1),
                               (date(2025, 9, 12), 0)]

    def test_the_series_needs_a_period(self, database):
        with pytest.raises(questions.BadPeriod):
            questions.daily_series(database)

    def test_a_series_longer_than_two_years_is_refused(self, database):
        """Eight thousand points is a file, not an answer."""
        with pytest.raises(questions.BadPeriod):
            questions.daily_series(database, since=date(2003, 1, 1),
                                   until=date(2026, 1, 1))


class TestCompare:
    def test_two_periods_side_by_side(self, database):
        found = questions.compare(
            database, state='GO',
            first=(date(2025, 9, 1), date(2025, 9, 30)),
            second=(date(2026, 10, 1), date(2026, 10, 31)))

        assert found.value == {'first': 2, 'second': 3, 'change': 1,
                               'change_percent': 50.0}

    def test_from_zero_there_is_no_percent(self, database):
        """Growth from nothing is not infinite per cent. It is
        undefined, and the answer says so."""
        found = questions.compare(
            database, state='PA',
            first=(date(2025, 1, 1), date(2025, 12, 31)),
            second=(date(2026, 1, 1), date(2026, 12, 31)))

        assert found.value['change_percent'] is None


class TestNear:
    def test_fires_within_a_radius(self, database):
        """a1 sits on the point; a2 is about 15 km away; a3 is
        hundreds."""
        found = questions.near(database, latitude=-16.1,
                               longitude=-49.2, km=20,
                               since=date(2026, 10, 1))

        assert found.value == 2

    def test_a_radius_too_large_is_refused(self, database):
        with pytest.raises(questions.BadRadius):
            questions.near(database, latitude=-16.1, longitude=-49.2,
                           km=5000)


class TestPoints:
    def test_points_come_as_geojson(self, database):
        found = questions.points(database, state='PA')

        feature = found.value['features'][0]
        assert found.value['type'] == 'FeatureCollection'
        assert feature['geometry']['coordinates'] == [
            pytest.approx(-52.3), pytest.approx(-3.3)]
        assert feature['properties']['city'] == 'ALTAMIRA'

    def test_too_many_points_are_cut_and_said(self, database):
        """A map of a million points freezes the page. The answer says
        it was cut, so nobody reads the sample as the total."""
        found = questions.points(database, limit=3)

        assert len(found.value['features']) == 3
        assert found.value['truncated'] is True
        assert found.value['total'] == 7
