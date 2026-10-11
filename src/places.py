"""The way a person names a place, turned into the way INPE writes it.

A filter that only takes INPE's spelling answers zero for every other
spelling, and zero fires is a believable, wrong answer. So a name is
either found or refused, never passed through.
"""

import difflib
import unicodedata

#: The 27 states, by their two-letter code, as INPE writes the names.
STATES = {
    'AC': 'ACRE', 'AL': 'ALAGOAS', 'AP': 'AMAPÁ', 'AM': 'AMAZONAS',
    'BA': 'BAHIA', 'CE': 'CEARÁ', 'DF': 'DISTRITO FEDERAL',
    'ES': 'ESPÍRITO SANTO', 'GO': 'GOIÁS', 'MA': 'MARANHÃO',
    'MT': 'MATO GROSSO', 'MS': 'MATO GROSSO DO SUL', 'MG': 'MINAS GERAIS',
    'PA': 'PARÁ', 'PB': 'PARAÍBA', 'PR': 'PARANÁ', 'PE': 'PERNAMBUCO',
    'PI': 'PIAUÍ', 'RJ': 'RIO DE JANEIRO', 'RN': 'RIO GRANDE DO NORTE',
    'RS': 'RIO GRANDE DO SUL', 'RO': 'RONDÔNIA', 'RR': 'RORAIMA',
    'SC': 'SANTA CATARINA', 'SP': 'SÃO PAULO', 'SE': 'SERGIPE',
    'TO': 'TOCANTINS',
}

BIOMES = ('Amazônia', 'Caatinga', 'Cerrado', 'Mata Atlântica', 'Pampa',
          'Pantanal')


class UnknownPlace(Exception):
    """A name that matches no state or biome."""


def plain(text):
    """Lower case, no accents, no outer spaces: how names are compared."""
    stripped = unicodedata.normalize('NFKD', text.strip().lower())
    return ''.join(c for c in stripped if not unicodedata.combining(c))


def _find(text, names):
    wanted = plain(text)
    for name in names:
        if plain(name) == wanted:
            return name
    close = difflib.get_close_matches(wanted, [plain(n) for n in names],
                                      n=1)
    hint = ''
    if close:
        hint = ' Did you mean ' + next(
            n for n in names if plain(n) == close[0]) + '?'
    raise UnknownPlace(f'{text!r} is not one of the names INPE uses.{hint}')


def state(text):
    """INPE's name for a state, from its name or two-letter code."""
    code = text.strip().upper()
    if code in STATES:
        return STATES[code]
    return _find(text, list(STATES.values()))


def biome(text):
    return _find(text, BIOMES)
