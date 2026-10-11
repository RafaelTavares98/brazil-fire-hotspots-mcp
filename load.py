"""Fill or refresh the store with every INPE file since 2003.

Usage: python load.py [path-to-database]

Safe to run every day: a detection already held is not saved again.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

import fetch  # noqa: E402
import store  # noqa: E402

#: The first year of INPE's yearly reference files.
FIRST_YEAR = 2003


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/fires.duckdb'
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    database = store.open_store(path)
    for step in fetch.plan(FIRST_YEAR, date.today()):
        try:
            if step[0] == 'year':
                new = fetch.load_year(database, step[1])
            else:
                new = fetch.load_month(database, step[1], step[2])
        except fetch.NotPublished as missing:
            print(f'{step}  not published: {missing}')
            continue
        print(f'{step}  {new:>7,} new', flush=True)
    print(f'held: {store.size(database):,}, days {store.days_held(database)}')


main()
