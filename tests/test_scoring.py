"""Scoring one agent answer against what it should have said.

Three kinds of expectation:

- numbers: every one must appear in the answer, in any language's way
  of writing it;
- contains: a name must appear, accents and case ignored;
- no_area: the answer must not state an area burned, because hotspots
  cannot measure one.

A rejected answer never passes: the guard caught the model inventing.
"""

import scoring


class Answer:
    def __init__(self, text, rejected=False):
        self.text = text
        self.rejected = rejected


class TestNumbers:
    def test_the_number_present_passes(self):
        case = {'numbers': [278299]}

        assert scoring.passes(case, Answer('There were 278,299.'))

    def test_brazilian_writing_passes(self):
        case = {'numbers': [278299]}

        assert scoring.passes(case, Answer('Foram 278.299 focos.'))

    def test_a_missing_number_fails(self):
        case = {'numbers': [431, 1625]}

        assert not scoring.passes(case, Answer('There were 431.'))

    def test_a_rejected_answer_fails_even_with_the_number(self):
        case = {'numbers': [5]}

        assert not scoring.passes(case, Answer('The tool said 5.',
                                               rejected=True))


class TestNames:
    def test_a_name_passes_without_accents(self):
        case = {'contains': ['NIQUELÂNDIA'], 'numbers': [110]}

        assert scoring.passes(case, Answer('Niquelandia, with 110.'))

    def test_a_missing_name_fails(self):
        case = {'contains': ['CORUMBÁ']}

        assert not scoring.passes(case, Answer('Poconé had the most.'))


class TestNoArea:
    def test_saying_it_cannot_passes(self):
        case = {'no_area': True}

        assert scoring.passes(case, Answer(
            'Hotspots do not measure the area burned.'))

    def test_stating_hectares_fails(self):
        case = {'no_area': True}

        assert not scoring.passes(case, Answer('About 12,000 hectares.'))

    def test_stating_square_km_fails(self):
        case = {'no_area': True}

        assert not scoring.passes(case, Answer('Cerca de 500 km² '
                                               'queimaram.'))


class TestTheSet:
    def test_the_golden_set_has_thirty_questions(self):
        assert len(scoring.load_golden()) == 30

    def test_every_case_says_what_it_expects(self):
        for case in scoring.load_golden():
            assert case['question']
            assert {'numbers', 'contains', 'no_area'} & set(case), case
