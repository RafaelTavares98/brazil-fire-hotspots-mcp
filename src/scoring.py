"""Scoring an agent answer against what it should have said.

The expected numbers come from outside the tools: INPE's own statistics
page where it publishes the figure, direct SQL on the store where it
does not. A rejected answer never passes, because the guard caught the
model inventing.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import agent
import places

GOLDEN = Path(__file__).resolve().parent.parent / 'eval' / 'golden.json'

#: A number followed by a unit of area: what hotspots cannot measure.
_AREA = re.compile(r'\d[\d.,]*\s*(hectares?|ha\b|km²|km2|quil[oô]metros '
                   r'quadrados|square)', re.IGNORECASE)


def load_golden(path=GOLDEN):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _says_number(text, wanted):
    wanted = Decimal(wanted).normalize()
    return any(wanted in agent._readings(token)
               for token in agent._NUMBER.findall(text))


def passes(case, answer):
    """True when the answer says everything the case expects."""
    if answer.rejected:
        return False
    text = answer.text
    if not all(_says_number(text, n) for n in case.get('numbers', [])):
        return False
    if not all(places.plain(name) in places.plain(text)
               for name in case.get('contains', [])):
        return False
    if case.get('no_area') and _AREA.search(text):
        return False
    return True
