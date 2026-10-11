# Explanation

[README](../README.md) · [Tutorial](tutorial.md) · [How-to](how-to.md) ·
[Reference](reference.md) · **Explanation**

Why the project is built this way. One argument per section.

---

## Why one satellite and not all of them

INPE's daily file has one row per detection, per satellite. On
2026-10-10 it held 44,263 rows. Most fires were seen by several
satellites, so the rows count sightings, not fires.

INPE's own totals use one satellite, AQUA in the afternoon, the same
since 2002. One satellite at one hour means one point per fire, and a
year that compares with every other year. This project counts the same
way, and so its totals equal INPE's. The cost is that it sees less: a
fire that burned only at night is missed.

## Why the reader is checked against INPE's page

A count that nobody can check is an opinion. INPE publishes its totals
by state and month. Comparing against them tested the whole chain
(download, reading, the satellite filter, storage, the SQL) in one step.
All 23 yearly totals for Brazil and nine monthly ones for 2026 agreed.

## Why DuckDB and not Postgres

The MCP server runs on the computer of whoever uses it. A database
server would mean installing it, a user, a password, and a service
always running. DuckDB is one file: copy it and it works. It counts
millions of rows in milliseconds, which is all six questions need. The
distance search uses the haversine formula in plain SQL, so no map
extension is needed either.

## Why loading twice changes nothing

A daily job will one day run twice, or stop halfway. Each fire is saved
once, by INPE's own id. Running the load again adds only what is
missing, so a failed morning is fixed by running it again.

## Why a place is found or refused, never passed through

INPE writes GOIAS with an accent, in capitals. A person writes Goias or
GO. A filter that only takes INPE's spelling answers zero for the
others, and zero fires is a believable, wrong answer. So every name is
matched ignoring case and accents, codes are accepted, and anything else
is refused with the closest name. In the thirty questions, "Goiaz" was
refused, the model read the hint, and asked again with the right name.

## Why every answer says where it came from

A count over days the database never loaded looks exactly like a quiet
week. So every answer carries the days held and a warning when the
question reaches past them. It also names INPE and the satellite, so a
reader can check the number at its source.

## Why every number is checked

A model can write a plausible number. The danger is that it looks
right. So the model only chooses tools and copies their numbers, and
code reads every number in its sentence. One that appears in no tool
result and not in the question throws the sentence away; code then says
what the tool returned.

The check reads numbers both ways. The model often answers in
Portuguese, where 1.625 means one thousand six hundred and twenty-five
and 73,5 means seventy-three and a half. The first live answer was
thrown away for exactly that, before the check learned both readings.

## Why the agent talks to the server and not to the database

The chat route could call the SQL directly. It does not: it goes
through the same MCP tools any assistant uses. Then the thirty-question
proof tests what other people will actually get, and a number in the
chat can never differ from a number another assistant reads.

## Why the golden answers come from outside the tools

A test that takes its expected number from the tool under test always
passes. The expected numbers came from INPE's statistics page where it
publishes them, and otherwise from SQL written by hand, apart from
questions.py.
