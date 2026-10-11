"""Turning the way a person names a state into the way INPE writes it.

INPE writes GOIÁS. A person, or a model, writes Goias, goiás or GO. A
filter that only takes INPE's spelling answers zero for the other three,
and zero fires is a believable, wrong answer.
"""

import pytest

import places


class TestStates:
    @pytest.mark.parametrize('typed', ['GOIÁS', 'Goiás', 'goias', 'GO',
                                       'go', ' Goiás '])
    def test_every_spelling_finds_the_state(self, typed):
        assert places.state(typed) == 'GOIÁS'

    def test_two_word_states(self):
        assert places.state('mato grosso do sul') == 'MATO GROSSO DO SUL'
        assert places.state('MS') == 'MATO GROSSO DO SUL'

    def test_all_27_are_known(self):
        assert len(places.STATES) == 27

    def test_an_unknown_state_is_refused_with_a_hint(self):
        """Never a silent zero. The refusal says what was meant."""
        with pytest.raises(places.UnknownPlace) as refused:
            places.state('Goiaz')

        assert 'GOIÁS' in str(refused.value)


class TestBiomes:
    @pytest.mark.parametrize('typed', ['Amazônia', 'amazonia', 'AMAZÔNIA'])
    def test_every_spelling_finds_the_biome(self, typed):
        assert places.biome(typed) == 'Amazônia'

    def test_all_six_are_known(self):
        assert len(places.BIOMES) == 6

    def test_an_unknown_biome_is_refused(self):
        with pytest.raises(places.UnknownPlace):
            places.biome('Savana')
