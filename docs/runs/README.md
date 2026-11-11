# Run log

One page per benchmark round: the exact configuration, the cost, what came out
and what was learned, with links to the traces in Langfuse. The numbers always
come from the round's results file, never from Langfuse.

| # | Date | Run | Model | Runs | `graph_tools` right | Real cost |
|---|---|---|---|---|---|---|
| [01](2026-10-10_01_claude-haiku-5.5.md) | 2026-10-10 | Claude Haiku 5.5, six arms | claude-haiku-5.5 | 312 | 45/52 | US$ 1.04 |
| [02](2026-10-12_02_qwen3.8-flash.md) | 2026-10-12 | Qwen3.8-flash, six arms | qwen3.8-flash | 312 | 44/52 | US$ 0.48 |
| [03](2026-10-12_03_kimi-k3.md) | 2026-10-12 | Kimi K3 (Bedrock), six arms | kimi-k3 | 312 | 47/52 | US$ 33.40 |
| [04](2026-10-13_04_claude-sonnet-4.6.md) | 2026-10-13 | Claude Sonnet 4.6 (Bedrock, with reasoning), six arms | us.anthropic.claude-sonnet-4-6 | 312 | 47/52 | ~US$ 28 (computed) |

The four rounds make up the design of the benchmark: two cheap models and two
expensive ones, one closed and one open-weight in each price band. The
conditions of each round (provider, reasoning, temperature) are in chapter 7,
section "Four models, paired by price".

The Portuguese version of these pages is in [`docs/pt-br/execucoes/`](../pt-br/execucoes/README.md).

## About the trace links

Each symbol in the tables (✅ right, ❌ hallucination, 🟡 abstention, ⚠️ format
error) opens the trace of that run in Langfuse: the prompt sent, every tool
call with its result, and the answer. **The Langfuse project is private**, so
the links only open for its members; everything needed to check a result is
in the results file itself.

Each line of the results file stores its own `trace_url`, and `ask.py` prints
the link. If the field is empty, `scripts/trace_links.py --write` finds the
traces by name and time and fills it in.

## How to log a new run

`scripts/run_benchmark.py` writes the page by itself when it finishes: it
creates `YYYY-MM-DD_NN_<file>.md` in this folder (configuration, commit,
command, real cost, results by group and arm, errors, an automatic reading,
every miss with the expected answer, and the traces) and adds the row to the
index above.

1. Use a results file of its own when it is not the main run:
   `python scripts/run_benchmark.py --repeats 1 --output data/benchmark/<name>_results.jsonl --title "<title>"`.
   `--no-report` skips the page.
2. The real cost comes from the OpenRouter key usage before and after
   (`https://openrouter.ai/api/v1/key`, field `usage`); with another provider it
   is "not measured". If it looks off, check call by call at
   `https://openrouter.ai/api/v1/generation?id=<id>` (field `provider_name`).
3. To write the page again for an existing results file:
   `python scripts/report_run.py --results <file>.jsonl [--title ...] [--cost ...]`.
4. Commit the results file, the summary and the page together. The automatic
   reading only describes the numbers; what they mean goes by hand in an extra
   section, when needed.
