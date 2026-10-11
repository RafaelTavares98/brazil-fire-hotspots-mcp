"""Ask the agent the thirty golden questions and score every answer.

Usage: python run_eval.py

Starts serve.py over stdio once, asks each question through it with the
real model, and writes eval/results.json. The bar is 28 of 30.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'src'))

from mcp.client.client import Client  # noqa: E402
from mcp.client.stdio import StdioServerParameters  # noqa: E402

import agent  # noqa: E402
import model  # noqa: E402
import scoring  # noqa: E402

BAR = 28


async def run(ask_model):
    server = StdioServerParameters(command=sys.executable,
                                   args=[str(HERE / 'serve.py')])
    results = []
    async with Client(server) as client:
        for number, case in enumerate(scoring.load_golden(), 1):
            start = time.perf_counter()
            try:
                found = await agent.ask(client, case['question'], ask_model)
            except model.ModelFailed as failure:
                found = agent.AgentAnswer(str(failure), [], rejected=True)
            passed = scoring.passes(case, found)
            results.append({
                'question': case['question'], 'passed': passed,
                'answer': found.text, 'draft': found.draft,
                'rejected': found.rejected,
                'calls': [[c.name, c.arguments] for c in found.calls],
                'seconds': round(time.perf_counter() - start, 1)})
            print(f'{number:2d} {"PASS" if passed else "FAIL"}  '
                  f'{case["question"][:60]}', flush=True)
    return results


def main():
    found_key = model.key()
    if not found_key:
        sys.exit('No DeepSeek key.')
    results = asyncio.run(run(model.deepseek(found_key)))
    (HERE / 'eval' / 'results.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    passed = sum(result['passed'] for result in results)
    print(f'{passed} of {len(results)} passed; the bar is {BAR}.')


main()
