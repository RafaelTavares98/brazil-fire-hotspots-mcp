"""Reading INPE's daily file into hotspots.

INPE writes one row per detection, per satellite. The same fire seen by
three satellites is three rows. Counting fires needs one satellite only,
the reference one, and the file does not say which that is.
"""

from datetime import datetime, timezone

import pytest

import hotspots


class TestReading:
    def test_every_row_is_read(self, sample):
        """Nothing is dropped on the way in, not even the repeated row.
        Dropping happens later, on purpose, where a test can see it."""
        assert len(sample) == 8

    def test_position_arrives_as_numbers(self, sample):
        """The file pads latitude with spaces. A string is no use on a
        map."""
        first = sample[0]

        assert first.latitude == pytest.approx(-16.1)
        assert first.longitude == pytest.approx(-49.2)

    def test_time_is_utc(self, sample):
        """INPE writes GMT. A time without a zone is read as local by
        whoever reads it next, and is three hours wrong in Brazil."""
        assert sample[0].seen_at == datetime(2026, 10, 1, 17, 5,
                                             tzinfo=timezone.utc)

    def test_place_names_keep_their_accents(self, sample):
        assert sample[0].city == 'NIQUELÂNDIA'
        assert sample[0].state == 'GOIÁS'
        assert sample[0].biome == 'Cerrado'

    def test_weather_fields_are_numbers(self, sample):
        first = sample[0]

        assert first.dry_days == 12
        assert first.rain_mm == 0.0
        assert first.fire_risk == 1.0
        assert first.power_mw == pytest.approx(35.5)


class TestMissingValues:
    def test_minus_999_means_unknown(self, sample):
        """INPE writes -999 where it has no value. Read as a number it
        would drag every average far below zero."""
        second = sample[1]

        assert second.dry_days is None
        assert second.fire_risk is None

    def test_an_empty_cell_means_unknown(self, sample):
        geostationary = sample[3]

        assert geostationary.dry_days is None
        assert geostationary.rain_mm is None
        assert geostationary.fire_risk is None

    def test_missing_power_is_unknown_not_zero(self, sample):
        """Zero megawatts would be a fire that gives off no heat."""
        assert sample[1].power_mw is None


class TestReferenceSatellite:
    def test_only_the_reference_satellite_counts(self, sample):
        """INPE counts fires with one satellite, so that one fire is one
        point and this year compares with last year."""
        counted = hotspots.reference_only(sample)

        assert {spot.satellite for spot in counted} == {'AQUA_M-T'}

    def test_a_repeated_row_counts_once(self, sample):
        """The file can carry the same detection twice. The id says so."""
        counted = hotspots.reference_only(sample)

        assert len(counted) == 4

    def test_the_reference_is_named_once(self):
        assert hotspots.REFERENCE_SATELLITE == 'AQUA_M-T'


class TestYearlyFile:
    """INPE's yearly file holds the reference satellite only, in another
    shape: no satellite column, no weather. It must become the same
    hotspot as the daily file, or every count downstream splits in
    two."""

    def test_every_row_is_read(self, yearly):
        assert len(yearly) == 3

    def test_the_id_is_the_detection_id(self, yearly):
        """foco_id, not id_bdq: the daily file names the same detection
        by foco_id, so both files agree on what one fire is."""
        assert yearly[0].detection_id == 'y1'

    def test_every_row_is_the_reference_satellite(self, yearly):
        assert {spot.satellite for spot in yearly} == {'AQUA_M-T'}

    def test_place_and_time_are_read(self, yearly):
        first = yearly[0]

        assert first.city == 'SOLIDÃO'
        assert first.state == 'PERNAMBUCO'
        assert first.seen_at == datetime(2025, 1, 1, 16, 52,
                                         tzinfo=timezone.utc)

    def test_weather_is_unknown_not_zero(self, yearly):
        first = yearly[0]

        assert first.dry_days is None
        assert first.rain_mm is None
        assert first.fire_risk is None
        assert first.power_mw is None

    def test_a_daily_file_is_not_a_yearly_one(self, sample_text):
        with pytest.raises(hotspots.NotAnInpeFile):
            hotspots.read_yearly(sample_text)


class TestContract:
    def test_a_file_without_the_columns_is_refused(self):
        """A changed format must stop the load, not fill the database
        with blanks."""
        with pytest.raises(hotspots.NotAnInpeFile):
            hotspots.read('a,b,c\n1,2,3\n')

    def test_an_empty_file_is_no_hotspots(self):
        """A quiet day in the rainy season is a real answer."""
        header = ('id,lat,lon,data_hora_gmt,satelite,municipio,estado,'
                  'pais,municipio_id,estado_id,pais_id,'
                  'numero_dias_sem_chuva,precipitacao,risco_fogo,bioma,frp\n')

        assert hotspots.read(header) == []
