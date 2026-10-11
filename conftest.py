"""Point pytest at the source, and hand every test the same sample.

The sample is eight rows written by hand, so every count a test expects
can be checked by eye against the file.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'src'))


@pytest.fixture
def sample_text():
    """One small INPE file, as the server sends it."""
    return (HERE / 'tests' / 'fixtures' / 'focos_sample.csv').read_text(
        encoding='utf-8')


@pytest.fixture
def yearly():
    """Three rows of INPE's yearly reference file, read into hotspots."""
    import hotspots
    text = (HERE / 'tests' / 'fixtures' / 'focos_yearly_sample.csv')
    return hotspots.read_yearly(text.read_text(encoding='utf-8'))


@pytest.fixture
def sample(sample_text):
    """The sample, read into hotspots, with nothing filtered out."""
    import hotspots
    return hotspots.read(sample_text)
