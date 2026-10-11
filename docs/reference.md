# Reference

[README](../README.md) · [Tutorial](tutorial.md) · [How-to](how-to.md) ·
**Reference** · [Explanation](explanation.md)

The facts: commands, tools, routes, fields and modules.

---

## Commands

| Command | What it does |
|---|---|
| `python load.py [db]` | download INPE's files into `data/fires.duckdb` |
| `python serve.py [db]` | run the MCP server over stdio |
| `python run_api.py [db]` | run the JSON API on port 8001 |
| `python ask.py "question"` | ask the agent once |
| `python run_eval.py` | ask the thirty golden questions and score them |
| `python check_links.py` | check every link in the markdown |

## Environment

| Variable | Used by | Default |
|---|---|---|
| `DEEPSEEK_API_KEY` | `model.key()` | none |

Without the variable, the key is looked for in the keychain, in this
order: `fire-mcp` / `deepseek`, `payables-panel` / `deepseek`,
`deepseek` / `api-key`.

## The data

INPE's files, at
`https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/`:

| File | Holds | Used for |
|---|---|---|
| `anual/Brasil_sat_ref/focos_br_ref_YYYY.zip` | reference satellite only, no weather | 2003 to last year |
| `mensal/Brasil/focos_mensal_br_YYYYMM.csv` | every satellite, with weather | this year |

The value `-999` and an empty cell both mean unknown, and are stored as
NULL.

## The table

One DuckDB table, `hotspots`, one row per fire:

| Column | Meaning |
|---|---|
| `detection_id` | INPE's id for the detection; the key |
| `latitude`, `longitude` | decimal degrees |
| `seen_at` | the moment of the satellite pass, UTC |
| `satellite` | always `AQUA_M-T` |
| `city`, `state`, `biome` | as INPE writes them, in capitals for places |
| `dry_days` | days without rain before the fire; this year only |
| `rain_mm` | rain that day; this year only |
| `fire_risk` | INPE's risk index, 0 to 1; this year only |
| `power_mw` | fire radiative power, in megawatts; this year only |

## The MCP tools

All six are read-only. Dates are `YYYY-MM-DD`, both ends included. A
state may be its name, in any case or accent, or its two-letter code.

| Tool | Takes | Returns |
|---|---|---|
| `count_fires` | state, city, biome, since, until | a number |
| `top_cities` | limit, state, biome, since, until | `[city, state, fires]`, biggest first, ties by name |
| `daily_series` | since, until (at most 731 days), state, city, biome | `[day, fires]`, quiet days as 0 |
| `compare_periods` | two since/until pairs, state, city, biome | first, second, change, change_percent |
| `fires_near` | latitude, longitude, km (at most 500), since, until | a number |
| `fire_points` | state, city, biome, since, until, limit (at most 5000) | GeoJSON, with total and truncated |

Every result has three keys:

| Key | Holds |
|---|---|
| `value` | the answer |
| `filters` | the filters as understood, places in INPE's spelling |
| `provenance` | source, source_url, satellite, held, warnings |

A warning appears when the period starts before or ends after the days
held. A refused call returns an error whose text says why: an unknown
place (with the closest name), a date not in `YYYY-MM-DD`, a period that
ends before it starts, or a radius over 500 km.

The resource `fires://about` holds the limits of the data in plain
text.

## The JSON API

The same six questions, plus the agent:

| Route | Same as |
|---|---|
| `GET /api/health` | days held, and whether a model is connected |
| `GET /api/count` | `count_fires` |
| `GET /api/top-cities` | `top_cities` |
| `GET /api/series` | `daily_series` |
| `GET /api/compare` | `compare_periods` |
| `GET /api/near` | `fires_near` |
| `GET /api/points` | `fire_points` |
| `POST /api/ask` | the agent: `{question, history}` in, `{text, rejected, calls}` out |

A refusal is a 400 with the reason in `detail`. `/api/ask` without a
model is a 503. Only user and assistant text from `history` is used,
the last six turns.

## The agent

| Constant | Value |
|---|---|
| `agent.MOST_ROUNDS` | 4 model calls per question at most |
| `model.MODEL` | `deepseek-flash`, temperature 0 |

A number passes the guard when any reading of it appears in a tool
result or in the question. `278,299`, `278.299` and `278299` read the
same; so do `73,5` and `73.5`.

## Tests

| File | What it defends |
|---|---|
| `test_hotspots.py` | both file shapes, unknown values, the reference satellite |
| `test_store.py` | saving once, NULL kept, days held |
| `test_fetch.py` | addresses, zip, monthly cut, the load plan |
| `test_places.py` | every spelling of a state or biome |
| `test_questions.py` | the six questions over seven hand-made fires |
| `test_provenance.py` | source and coverage warnings |
| `test_server.py` | the tools through a real MCP client |
| `test_agent.py` | the loop and the number guard |
| `test_model.py` | the DeepSeek client, fake transport |
| `test_scoring.py` | marking answers, and the golden set's shape |
| `test_web.py` | every route, and the history filter |
