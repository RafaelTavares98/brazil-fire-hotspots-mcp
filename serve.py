"""Run the MCP server over stdio, the way an AI assistant starts it.

Usage: python serve.py [path-to-database]

The store is opened read-only, so the daily load can run beside it.
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'src'))

import duckdb  # noqa: E402

import server  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else HERE / 'data' / 'fires.duckdb'
server.build(duckdb.connect(str(path), read_only=True)).run()
