"""Serve the web API on http://localhost:8001.

Usage: python run_api.py [path-to-database]

The store is opened read-only. The chat route uses DeepSeek when a key
is found, and says why it cannot answer when none is.
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'src'))

import duckdb  # noqa: E402
import uvicorn  # noqa: E402

import model  # noqa: E402
import web  # noqa: E402

PORT = 8001

path = sys.argv[1] if len(sys.argv) > 1 else HERE / 'data' / 'fires.duckdb'
found_key = model.key()
app = web.create(duckdb.connect(str(path), read_only=True),
                 model=model.deepseek(found_key) if found_key else None)
uvicorn.run(app, host='127.0.0.1', port=PORT)
