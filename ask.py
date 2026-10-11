"""Ask the agent one question from the command line.

Usage: python ask.py "Quantos focos em Goiás em setembro de 2026?"

The agent starts serve.py over stdio, exactly as any MCP client would.
"""

import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'src'))

from mcp.client.stdio import StdioServerParameters  # noqa: E402

import agent  # noqa: E402
import model  # noqa: E402


def main():
    found_key = model.key()
    if not found_key:
        sys.exit('No DeepSeek key. Set DEEPSEEK_API_KEY or store it with: '
                 'python -m keyring set fire-mcp deepseek')
    server = StdioServerParameters(command=sys.executable,
                                   args=[str(HERE / 'serve.py')])
    found = asyncio.run(agent.ask_server(server, sys.argv[1],
                                         model.deepseek(found_key)))
    for call in found.calls:
        print(f'  tool {call.name} {call.arguments}')
    if found.rejected:
        print(f'  [rejected draft] {found.draft}')
    print(found.text)


main()
