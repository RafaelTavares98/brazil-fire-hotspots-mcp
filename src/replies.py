"""One answer, in the shape every door hands out.

The MCP server and the web API both answer the same questions. Both
hand back the value, the filters as understood, and where it all came
from; both turn a refusal into a sentence. That shape lives here once,
so the two doors cannot drift apart.
"""

from datetime import date

import places
import provenance
import questions


class BadDate(Exception):
    """Text that is not a date in the form the doors take."""


class Refused(Exception):
    """A question that cannot be answered, said in a sentence."""


#: Refusals a reader can act on. Anything else is a fault, and stays one.
REFUSALS = (BadDate, places.UnknownPlace, questions.BadPeriod,
            questions.BadRadius)


def day(text):
    """A date from YYYY-MM-DD text, or None for no text."""
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise BadDate(f'{text!r} is not a date. Write it as YYYY-MM-DD.')


def plain(value):
    """Dates become text; lists and dicts are walked."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def _period(filters):
    """The widest span the filters asked about, as dates."""
    starts = [filters.get('since')] + [filters.get(key, [None])[0]
                                       for key in ('first', 'second')]
    ends = [filters.get('until')] + [filters.get(key, [None, None])[1]
                                     for key in ('first', 'second')]
    starts = [date.fromisoformat(text) for text in starts if text]
    ends = [date.fromisoformat(text) for text in ends if text]
    return (min(starts) if starts else None, max(ends) if ends else None)


def reply(database, ask):
    """Ask one question. A refusal is raised as Refused, with its reason;
    every answer carries where it came from."""
    try:
        answer = ask()
    except REFUSALS as refused:
        raise Refused(str(refused)) from refused
    since, until = _period(answer.filters)
    return {'value': plain(answer.value), 'filters': answer.filters,
            'provenance': provenance.describe(database, since, until)}
