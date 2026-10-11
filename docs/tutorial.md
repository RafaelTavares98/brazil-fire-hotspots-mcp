# Tutorial: one answer, end to end

[README](../README.md) · **Tutorial** · [How-to](how-to.md) ·
[Reference](reference.md) · [Explanation](explanation.md)

By the end of this lesson you will have built the fire database, asked
the MCP server a question directly, and then asked the AI agent the same
question in plain Portuguese.

Allow twenty minutes, most of it waiting for the download.

## Before you start

You need Python 3.10 or newer:

```bash
python --version
```

Move into the project and install what it needs:

```bash
cd Portfolio/manual/03-fire-mcp
pip install -r requirements.txt
```

## Step 1: prove the project works

```bash
python -m pytest
```

You should see `139 passed`. No test touches the internet. If anything
fails, stop here.

## Step 2: build the database

```bash
python load.py
```

The program downloads one file per year from 2003, then one per month
of this year, and prints how many fires each added:

```
('year', 2003)  341,237 new
...
('month', 2026, 9)   24,382 new
held: 5,325,814, days (2003-01-01, 2026-10-10)
```

Run it again. Every line now says `0 new`: a fire already held is never
saved twice. Why that matters:
[loading twice changes nothing](explanation.md#why-loading-twice-changes-nothing).

## Step 3: check one number against INPE

Open INPE's statistics page for Goias:
https://data.inpe.br/queimadas/estatisticas/?tipo=estados&item=goias

Find September in the 2026 row. Then ask the database the same thing:

```bash
python -c "import sys; sys.path.insert(0,'src'); import duckdb, questions; from datetime import date; db=duckdb.connect('data/fires.duckdb', read_only=True); print(questions.count(db, state='GO', since=date(2026,9,1), until=date(2026,9,30)).value)"
```

Both say 431. They agree because the count uses the same single
satellite INPE uses:
[one satellite, not all of them](explanation.md#why-one-satellite-and-not-all-of-them).

## Step 4: ask the agent

Connect a DeepSeek key first, as
[the how-to](how-to.md#connect-the-deepseek-key) shows. Then:

```bash
python ask.py "Goias teve mais focos em setembro de 2026 ou em setembro de 2025?"
```

You see the tool the model chose, then its sentence:

```
  tool compare_periods {'first_since': '2025-09-01', ...}
Em Goias, setembro de 2026 registrou 431 focos, contra 1.625 em
setembro de 2025, uma queda de 1.194 focos (-73,5%).
```

Every number in that sentence was checked against what the tool
returned. The check accepts 1.625 as Portuguese for 1625:
[the number guard](explanation.md#why-every-number-is-checked).

## What you have learned

- The database is built from INPE's own files, and its counts equal
  INPE's published totals.
- The MCP server offers six tools; the model only chooses among them.
- A sentence with a number no tool returned never reaches the reader.

## Where to go next

- [How-to guide](how-to.md) to connect the server to an AI assistant.
- [Reference](reference.md) for every tool and route.
- [Explanation](explanation.md) for why it is built this way.
