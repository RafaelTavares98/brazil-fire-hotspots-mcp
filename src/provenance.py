"""Where every answer came from, and what it does not cover.

A count over days the store never loaded looks exactly like a quiet
week. So every answer names its source and satellite, the days the store
really holds, and a warning when the question reaches past them.
"""

import hotspots
import store

SOURCE = 'INPE, Programa Queimadas'
SOURCE_URL = 'https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/'

#: The limits of the data, read by a model before it answers. Drawn from
#: what the papers that use this data repeat.
ABOUT = f"""\
Fire hotspots over Brazil, from {SOURCE} ({SOURCE_URL}).

How they are counted
- One satellite only, {hotspots.REFERENCE_SATELLITE}, the one INPE uses for
  its own totals. One pass a day in the early afternoon, the same since
  2003, so years compare with each other.
- One point per detection. Yearly totals here equal INPE's published ones.

What a hotspot is not
- A hotspot is a pixel about 1 km wide that was hotter than its
  surroundings. It is a count of detections, not the area burned.
- A large fire can show as many hotspots; a small or short fire, or one
  under cloud or thick forest canopy, can show none. Small fires are
  missed most.
- It does not say who lit the fire, or why.

How to quote a number
- Give the period and the place it covers, and say it is INPE's
  reference-satellite count.
"""


def _warnings(held, since, until):
    if held is None:
        return ['The store is empty. Run load.py.']
    first, last = held
    found = []
    if since and since < first:
        found.append(f'The data starts on {first.isoformat()}. Days before '
                     f'it are not counted.')
    if until and until > last:
        found.append(f'The data ends on {last.isoformat()}. Days after it '
                     f'are not counted yet.')
    return found


def describe(database, since=None, until=None):
    """The source, the days held, and what the period leaves uncovered."""
    first, last = store.days_held(database)
    held = None if first is None else (first, last)
    return {
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'satellite': hotspots.REFERENCE_SATELLITE,
        'held': None if held is None else [first.isoformat(),
                                           last.isoformat()],
        'warnings': _warnings(held, since, until),
    }
