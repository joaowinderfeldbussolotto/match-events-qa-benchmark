# 6. How to run, from scratch

This chapter takes you from a bare computer to the benchmark report. There are
two paths that end up in the same place:

- **Path A, local Python**: Neo4j runs in Docker and the scripts run in your
  Python. It is the fastest way to work on the code.
- **Path B, everything in Docker**: the scripts also run inside a container.
  No Python install needed.

The steps are the same in both; only the command prefix changes.

---

## 6.1 Prerequisites

| What | For what | Path |
|---|---|---|
| Docker (with `docker compose`) | running Neo4j | A and B |
| Python **3.11** | running the scripts | A only |
| An LLM API key | the benchmark arms | A and B |
| An embeddings API key | only the `vector` arm | A and B |
| ~3 GB free | Neo4j image, data, models | A and B |

Why Python 3.11 and not the newest? The `socceraction` library, which does the
SPADL conversion, does not install on Python 3.13 or later.

---

## 6.2 Configure `.env`

All settings live in a `.env` file at the project root, which **does not go
into Git** (it holds secret keys). Start by copying the template:

```bash
cp .env.example .env
```

And fill it in:

| Variable | What it is | Example |
|---|---|---|
| `LLM_PROVIDER` | who serves the model | `openrouter`, `anthropic`, `gemini`, `mistral` or `bedrock` |
| `LLM_API_KEY` | that provider's key | `sk-or-...` |
| `LLM_MODEL` | the model's name at the provider. On OpenRouter, always `lab/model` | `z-ai/glm-5.3-flash` |
| `LLM_MAX_RETRIES` | how many times the SDK itself retries after a temporary error (rate limit, server down) | `5` (use 6 to 8 on free keys) |
| `LLM_MAX_TOKENS` | cap on the tokens the model may **write** per answer | `16000` |
| `LLM_REASONING_EFFORT` | OpenRouter and Bedrock: how much the model "thinks" before answering. On Bedrock it turns on extended thinking with temperature 1. Empty = the model's default | empty |
| `LLM_PROVIDER_ORDER` | OpenRouter only: a pinned provider (slug from the model's page, e.g. `baidu/fp8`), with no fallback to another. Empty = OpenRouter chooses | empty |
| `LLM_AWS_REGION` | Bedrock only (`LLM_PROVIDER=bedrock`, `pip install -e ".[bedrock]"`): the endpoint's region. `LLM_MODEL` is the model ID on Bedrock and `LLM_API_KEY` the Bedrock API key; empty = default AWS credentials | empty |
| `LLM_PROMPT_CACHE` | `false` removes the cache point from prompts (for a model without prompt caching at the provider). It does not change what the model reads | `true` |
| `EMBEDDER_PROVIDER` | who produces the embeddings for the `vector` arm. OpenRouter does not offer embeddings, so another one is needed | `gemini` or `mistral` |
| `EMBEDDER_API_KEY`, `EMBEDDER_MODEL` | embeddings key and model | `gemini-embedding-001` |
| `NEO4J_URI` | Neo4j's address | `bolt://localhost:7687` on path A; on B the compose file sets it |
| `NEO4J_USER`, `NEO4J_PASSWORD` | Neo4j user and password | `neo4j` / `changeme` |
| `LANGFUSE_*` | optional; viewing the runs (chapter 5) | empty turns it off |
| `STATSBOMB_MATCH_IDS` | the match | `3869685` (the final) |

**Why does `NEO4J_URI` change?** Inside Docker, Neo4j is reached by the service
name (`neo4j`). Outside, through your computer (`localhost`). `local_setup.sh`
(path A) switches it automatically and keeps a copy of the original in
`.env.bak-local`.

---

## 6.3 Path A: local Python

### All at once

```bash
scripts/local_setup.sh
source .venv/bin/activate
```

The script does the following, in this order, and can be run again without
breaking anything:

1. checks Docker and installs `uv` (a fast Python installer) if missing;
2. creates the `.venv` environment with Python 3.11 and installs the project;
3. creates or adjusts `.env` (`NEO4J_URI` to `localhost`);
4. starts **only Neo4j** in Docker, waits for it to be ready and checks that
   the GDS plugin loaded. If the container could not download the plugin
   (it happens on networks with broken DNS), the script downloads it through
   your computer and installs it;
5. runs layers 0, 1/1b and 2.

**None of this spends API credits.** The first time, step 5 is the slowest: it
downloads the 16 knockout games of the World Cup and trains the xT and VAEP
models on them. After that, it uses the models stored in `data/models/`, and
layer 0 of the final takes a few seconds.

Options: `--sem-camadas` (environment and Neo4j only, no layers) and
`--testes` (runs `pytest` at the end).

### Step by step, by hand

If you prefer to see each step:

```bash
docker compose up -d neo4j                 # starts Neo4j (GDS and APOC included)
python scripts/download_statsbomb.py       # downloads the final's raw JSON
python scripts/run_pipeline.py             # layer 0
python scripts/build_graph.py              # layers 1 and 1b
python scripts/run_analysis.py             # layer 2
```

What to expect from each one (real output, trimmed; the scripts print in
Portuguese):

```text
# run_pipeline.py
[3869685] 4527 eventos kloppy -> 2585 ações SPADL (537 fases de posse) em 2.01s

# build_graph.py
estatísticas de jogador 3869685: 34 nós
estatísticas de time 3869685: 2 nós
[3869685] 8004 escritas em 0.88s

# run_analysis.py
[3869685] 24 padrões táticos: {'pivo_estrutural': 2, 'terceiro_homem': 6, ...}
```

That is: 4,527 kloppy events become 2,585 SPADL actions (537 possession
phases); 34 player stat nodes and 2 team stat nodes; 8,004 writes; 24 tactical
patterns.

(`run_pipeline.py` counts 4,527 events, not the 4,407 of the JSON, because the
reading library, `kloppy`, creates derived events: for example, 80 "ball out"
events and the cards as separate events.)

---

## 6.4 Path B: everything in Docker

```bash
cp .env.example .env                       # fill in the keys
docker compose up -d --build               # starts neo4j + app
```

The `app` service is a container with the project installed, which sits idle
waiting for commands. Check with `docker compose config --services`: it should
list `neo4j` and `app`.

Then every path A command gets the `docker compose exec app` prefix:

```bash
docker compose exec app python scripts/download_statsbomb.py
docker compose exec app python scripts/run_pipeline.py
docker compose exec app python scripts/build_graph.py
docker compose exec app python scripts/run_analysis.py
docker compose exec app python scripts/check_ground_truth.py
docker compose exec app python scripts/smoke_llm.py
docker compose exec app python scripts/run_benchmark.py --sample
```

Good to know:

- `src/`, `scripts/`, `config/` and `data/` are **mounted from your computer**
  inside the container. Editing code or questions does not require rebuilding
  the image, and the results show up directly in `data/benchmark/`. Only
  changes to `pyproject.toml` (dependencies) need `docker compose up -d --build`.
- `pytest` is not installed in the image; run the tests through path A.
- To stop: `docker compose down`. The database is kept in a volume;
  `docker compose down -v` deletes the database too.

---

## 6.5 Check before spending: ground truth and model

Two cheap checks before the benchmark:

```bash
python scripts/check_ground_truth.py
```

Compares the ground truth with the graph, with no LLM (chapter 3). It must end
with `52/52 agree`. If it does not, something is different in the data, and
the benchmark should not be run until the difference is understood.

```bash
python scripts/smoke_llm.py
```

Makes **one** call to your model to check the two abilities the benchmark
depends on: calling tools and answering in the `Answer` format. The output
format (the numbers vary):

```text
provider=openrouter  model=z-ai/glm-5.3-flash
tool calling:      ok
structured output: ok
tokens in/out: <input>/<output>  latency: <seconds>s
```

If `FAILED` shows up, the chosen model does not work for the benchmark (it
either did not call the tool or did not follow the format). Change
`LLM_MODEL`.

---

## 6.6 Run the benchmark

### First, the sample

```bash
python scripts/run_benchmark.py --sample
```

Runs **the first question of each type** (f01, a01, n03, s01, u01, t06, c01,
q01, p01, b02), on the configured arms (below), once. With the two default
arms that is 20 runs. It costs cents and shows whether everything works end to
end. Each run prints a line in this format:

```text
[7/20] a01 events_in_prompt r1: ok (<input tokens>/<output tokens> tok, <seconds>s)
```

The outcome can be `ok`, `wrong`, `abstention` or `format_error` (chapter 5).

### Which arms to run

The [`config/benchmark.yaml`](../config/benchmark.yaml) file says which arms
`run_benchmark.py` and `ask.py` use when the command line says nothing else:

```yaml
arms: [events_in_prompt, graph_tools]
```

For the round that consolidates the results, list all six: the five main ones
and `text_to_cypher` (chapter 4, section 4.7), which is optional and only runs
when listed. Every published round uses all six. On the command line, `--arms`
(in `run_benchmark.py`) or `--arm` (in `ask.py`) overrides the file.

### Then, the full benchmark

```bash
python scripts/run_benchmark.py --fresh
```

With the six arms listed, that is 52 questions × 6 arms × 3 repeats = **936
runs**, one at a time (`--repeats 1` makes 312). `--fresh` empties the results
file first (without it, the script refuses to start if there are already
results, so as not to mix the sample with the full run or delete paid data by
accident).

**How much does it cost?** The heaviest arms are `events_in_prompt` (~115
thousand input tokens per question on Haiku, almost all read from the cache
from the second one on), `graph_tools` (~76 thousand per question) and
`text_to_cypher` (~51 thousand). The cost of one repeat (312 runs) on each
model run so far:

| Model | Via | Cost |
|---|---|---|
| Claude Haiku 5.5 | OpenRouter | US$ 1.04 |
| Qwen3.8-flash | OpenRouter, Alibaba provider | ~US$ 0.49 |
| Claude Sonnet 4.6 | Bedrock directly, thinking on | ~US$ 18 to 26 |
| Kimi K3 | OpenRouter with an own Bedrock key | US$ 33.40 |

The real cost shows on the run's page (in [`docs/runs/`](runs/README.md)),
read from the OpenRouter key's usage before and after; on Bedrock directly it
is computed from the tokens and the list prices.

**How long does it take?** It depends on the model and the provider. One
repeat took about 1 hour on Haiku and Qwen, 1h45 on Sonnet 4.6 and 3h on Kimi
K3. Reasoning models go over 1 minute per question in `events_in_prompt`.

### If it drops halfway

Each run is written **right after** it ends. If the internet drops or the
provider fails, nothing is lost besides the run in progress:

```bash
python scripts/run_benchmark.py --resume
```

picks up where it stopped. Provider errors (server down, rate limit exceeded
even after the SDK's retries) **are not written**, and `--resume` redoes them.
The script says at the end how many there were.

### Other options

| Option | What it does | Example |
|---|---|---|
| `--repeats N` | number of repeats (default 3) | `--repeats 1` |
| `--arms a,b` | only some arms | `--arms stats_in_prompt,graph_tools` |
| `--questions x,y` | only some questions | `--questions f01,s02` |
| `--output file` | writes to another file (the report goes next to it, with the same name + `_summary.md`) | `--output data/benchmark/test.jsonl` |

### Running with another model

Each model evaluated is a round of its own, in its own file
(`--output data/benchmark/<model>_results.jsonl`, with `--title`). The code
does not change: only the `.env` variables (or the command line).

**Through OpenRouter, with a pinned provider.** The same model is served by
several providers, with different prices and quantizations.
`LLM_PROVIDER_ORDER` pins one of them (the *slug* from the model's page, e.g.
`alibaba` or `amazon-bedrock/us-east-2`) and sends `allow_fallbacks: false`: if
that provider fails, the call fails, instead of going to another, more
expensive one. Each model's providers, with price, context and whether they
take tools, are at `https://openrouter.ai/api/v1/models/<model>/endpoints`.

```bash
LLM_PROVIDER=openrouter LLM_MODEL=qwen/qwen3.8-flash LLM_PROVIDER_ORDER=alibaba \
LLM_REASONING_EFFORT=none \
python scripts/run_benchmark.py --arms no_context,vector,events_in_prompt,stats_in_prompt,graph_tools,text_to_cypher \
  --repeats 1 --fresh --output data/benchmark/qwen3.8-flash_results.jsonl --title "Qwen3.8-flash, six arms"
```

**With your own Bedrock key on OpenRouter (BYOK).** If you register an Amazon
Bedrock API key in OpenRouter's integrations, the calls pinned to
`amazon-bedrock/...` are billed on AWS, not on the OpenRouter balance. In the
key's settings, tick **"Never use OpenRouter's Amazon Bedrock capacity"**:
without it, when your key fails, OpenRouter retries the call with its own
account and charges your balance (it happened once in the Kimi K3 round). The
OpenRouter key is still needed: it authenticates the call.

**On Bedrock, directly.** `LLM_PROVIDER=bedrock` uses the Bedrock Converse API
(it needs `pip install -e ".[bedrock]"`). `LLM_API_KEY` is the Bedrock API key,
`LLM_AWS_REGION` the region and `LLM_MODEL` the ID of the model or of the
inference profile:

```bash
LLM_PROVIDER=bedrock LLM_MODEL=us.anthropic.claude-sonnet-4-6 LLM_AWS_REGION=us-east-2 \
LLM_API_KEY="$BEDROCK_API_KEY" LLM_REASONING_EFFORT=medium python scripts/smoke_llm.py
```

The models the key can see in a region:
`curl -H "Authorization: Bearer $BEDROCK_API_KEY" https://bedrock.<region>.amazonaws.com/foundation-models`.
Several models only accept the inference profile ID (prefix `us.` or
`global.`), not the plain ID.

**Reasoning.** `LLM_REASONING_EFFORT` (`none`, `low`, `medium`, `high`) goes to
OpenRouter as `reasoning.effort` and to Bedrock as PydanticAI's extended
thinking, which on Claude requires temperature 1 (the code sets it). Some
providers refuse reasoning together with the structured final answer (Alibaba,
with Qwen): then, `none`.

**Before the full round, a screening.** Two questions on two arms cost cents
and show whether the model calls the tools, follows the format and whether the
cache works (`cache_read_tokens` from the 2nd question on):

```bash
python scripts/run_benchmark.py --questions f01,n12 --arms events_in_prompt,graph_tools \
  --repeats 1 --fresh --no-report --output /tmp/screening.jsonl
```

**Merging reruns.** To replace some lines of a round with another run (another
output cap, another effort), write the rerun to a separate file and merge it
with `scripts/merge_results.py`, in which the last file wins; the source files
stay as they are. This is how the Sonnet 4.6 file,
`claude-sonnet-4.6_results.jsonl`, was put together (chapter 7).

### The result

- `data/benchmark/results.jsonl`: one line per run (chapter 5);
- `data/benchmark/summary.md`: the report.

To rebuild the report without calling any model:

```bash
python scripts/summarize.py
```

Both files are versioned in Git: the benchmark result is part of the project.

To record the run, follow the guide in [`docs/runs/`](runs/README.md). It
includes a table of links to the traces, generated by
`python scripts/trace_links.py --results <file>`.

---

## 6.7 Asking free questions (or a single question)

To explore, investigate an error or see how each arm behaves, without writing
anything to `results.jsonl`. There are three ways:

**Interactive mode**, for several free questions in a row:

```bash
python scripts/ask.py --arm graph_tools
```

```text
model: openrouter:anthropic/claude-haiku-5.5 | arms: graph_tools
Free questions about the 2022 World Cup final, one per line. Empty line or 'sair' to quit.

pergunta> Quem tocou mais na bola?
=== graph_tools  (<seconds>s, tokens in/out <input>/<output>)
  tool: query_actions(filters=None, group_by=['player'], metric='count', top=5)
  answer:  <the model's reasoning, as text>
  players: <players> | value: <number> | no_data: no
  trace:   https://us.cloud.langfuse.com/project/.../traces/...

pergunta> sair
```

("Quem tocou mais na bola?" is "Who touched the ball the most?". Questions can
be asked in any language, but the benchmark ones are in Portuguese.)

Without `--arm`, each question goes to the arms in `config/benchmark.yaml`.
That is useful for comparing, but more expensive: `events_in_prompt` sends
~100 thousand tokens per question. With prompt caching, the first question
pays for the write and the following ones, asked within 5 minutes, come out
much cheaper.

**A free question**, in a single command:

```bash
python scripts/ask.py "Quem tocou mais na bola?"                  # on the configured arms
python scripts/ask.py "Quem tocou mais na bola?" --arm stats_in_prompt
```

**A benchmark question**, with ground truth and verdict:

```bash
python scripts/ask.py --question s03                      # on the configured arms
python scripts/ask.py --question s03 --arm graph_tools    # a single arm
python scripts/ask.py --question s03 --show-prompt        # also shows the prompt sent
```

A free question **has no ground truth**: the answer is shown, not graded. Every
arm answers in the same format as the benchmark (`rationale`, `players`,
`value`, `no_data`), so the explanation is in the `answer` field (the
`rationale`). Open questions ("how did Argentina build up play?") work, but
the format was designed for closed questions, and the answer comes summarized
in that field.

For a benchmark question, the output also shows the ground truth and the
verdict: `CORRECT`, `WRONG`, `ABSTENTION` or `FORMAT ERROR`.

## 6.8 Tests

```bash
pytest
```

The tests check the scoring of the answers, the ground truth, the tools, how
the prompts are built and layers 0 to 2, without calling any LLM (they use the
library's fake models). Those that need Neo4j or the downloaded data are
**skipped** when they are not available. That is not a failure: start Neo4j
and run the layers so that they all run.

---

## 6.9 Common problems

| Symptom | Likely cause | What to do |
|---|---|---|
| `cannot run: LLM_API_KEY and LLM_MODEL must be set in .env` | `.env` without a key or model | fill it in (6.2). For the `vector` arm, also `EMBEDDER_*` |
| `Temporary failure in name resolution` when downloading the data | the container cannot resolve domain names (common in Codespaces) | `docker compose down && docker compose up -d` and try again. If it persists, use path A: the download done on your computer goes to `data/raw/` and is reused |
| `Couldn't connect to localhost:7687` | Neo4j is not up, or `NEO4J_URI` points to the wrong place | `docker compose ps`; on path A, `NEO4J_URI=bolt://localhost:7687` |
| `run_analysis.py` fails with `gds...` | the GDS plugin did not load in Neo4j | run `scripts/local_setup.sh`, which installs it through your computer |
| `already has N runs. Use --resume to continue or --fresh to start over.` | there are already results in the file | `--resume` to continue; `--fresh` to start from scratch (deletes the previous ones) |
| many `format_error` in one arm | the model does not handle structured output well | run `smoke_llm.py`; consider another model |
| context/size error in `events_in_prompt` | the model takes fewer than ~70 thousand tokens | use a model with a larger window, or run without that arm (`--arms`) |
| `PROVIDER ERROR` on several runs | the provider's rate limit | wait and run `--resume`; on a free key, raise `LLM_MAX_RETRIES` |
| `Model token limit (N) exceeded before any response was generated` | the model spent the whole cap thinking (reasoning models) | raise `LLM_MAX_TOKENS` or lower `LLM_REASONING_EFFORT` |
| `401 User not found` from OpenRouter | the OpenRouter key is disabled (even with BYOK, it authenticates the call) | re-enable the key; to avoid spending balance, put a limit on it and use the pinned provider |
| `403 ... explicit deny in a service control policy` from Bedrock | the AWS organization's policy denies the call in that region or model | try another region (`us-east-2` worked on the author's account); only the account administrator changes the policy |
| `... is not available for this account` from Bedrock | the model is not enabled on the account | choose another model; the account's list comes from `foundation-models` above |
| `Invocation of model ID ... with on-demand throughput isn't supported` | the model requires an inference profile | use the prefixed ID, e.g. `us.moonshotai.kimi-k3` |
| `temperature may only be set to 1 when thinking is enabled` | Claude reasoning with temperature 0 | use `LLM_REASONING_EFFORT` (the code adjusts the temperature) |
| `The tool_choice parameter does not support being set to required ... in thinking mode` | the provider refuses structured output with reasoning | `LLM_REASONING_EFFORT=none` |
| `Tool '...' exceeded max retries` with arguments as JSON text | the model sent an object as text | already handled by the code; if it shows up, see in the trace which argument failed |
| `502 Upstream error from Amazon Bedrock` | a transient Bedrock failure | `--resume` redoes only the missing ones |
