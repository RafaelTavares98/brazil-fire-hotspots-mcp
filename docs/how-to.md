# How-to guide

[README](../README.md) · [Tutorial](tutorial.md) · **How-to** ·
[Reference](reference.md) · [Explanation](explanation.md)

Recipes for people who know the project. Each one stands alone.

---

## Connect the server to Claude Code

Add the server once, pointing at this folder:

```bash
claude mcp add fire-mcp -- python "C:/path/to/03-fire-mcp/serve.py"
```

Then ask Claude about fires in Brazil. It lists the six tools and calls
them itself. The server opens the database read-only, so the daily load
can run beside it.

## Connect the server to Claude Desktop

Add this to `claude_desktop_config.json`, under `mcpServers`:

```json
"fire-mcp": {
  "command": "python",
  "args": ["C:/path/to/03-fire-mcp/serve.py"]
}
```

Restart Claude Desktop.

## Connect the DeepSeek key

Only `ask.py`, `run_eval.py` and the `/api/ask` route need it. The
environment comes first:

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
```

or the system keychain, which keeps it out of files and history:

```bash
python -m keyring set fire-mcp deepseek
```

A key the earlier projects stored under `payables-panel` or `deepseek`
is found too. Where each is looked for:
[the environment](reference.md#environment).

## Refresh the data every day

`load.py` adds only what is new, so running it daily is safe. On
Windows, a scheduled task at 06:00:

```powershell
schtasks /create /tn "fire-mcp load" /sc daily /st 06:00 /tr "python C:\path\to\03-fire-mcp\load.py C:\path\to\03-fire-mcp\data\fires.duckdb"
```

INPE publishes the monthly file through yesterday, so the morning load
catches the day before.

## Serve the JSON API

```bash
python run_api.py
```

It listens on http://localhost:8001. Try
http://localhost:8001/api/count?state=GO and
http://localhost:8001/docs for every route.

## Run the thirty questions again

```bash
python run_eval.py
```

It needs the key, costs a few cents, and writes `eval/results.json`.
Run it after any change to a tool description or to the agent's
instructions: those are what the model reads to choose.

## Add a question to the golden set

Add one object to `eval/golden.json`:

```json
{"question": "...", "numbers": [123], "truth": "where 123 came from"}
```

Use `contains` for a name that must appear, and `no_area` for a
question the tools must decline. Take the expected number from INPE's
page or from SQL written by hand, never from the tools themselves.
`tests/test_scoring.py` expects exactly thirty; change it with the set.

## Check every link in the docs

```bash
python check_links.py
```
