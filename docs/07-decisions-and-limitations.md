# 7. Decisions, problems found and limitations

This chapter gathers the "why" of the project: the choices that shaped the
benchmark, the known problems in the data (and how they are handled) and what
the benchmark **cannot** say. Read it before drawing conclusions from the
results.

---

## 7.1 Design decisions

### Simplicity over completeness

The project started as a bigger system: a web API, a hybrid search layer
(Graphiti) and other LLMs acting as judges of the answers. All of that was
removed. Each extra piece was one more thing that could fail and one more
variable muddying the central question. What is left is the minimum needed to
compare six ways of giving data to a model, in a verifiable way.

### A single match

Only the 2022 World Cup final. That keeps the ground truth small enough to be
checked by hand and the event table small enough to fit in a model's context
(the `events_in_prompt` arm needs that). The price is in 7.3.

### The ground truth never comes from the database being evaluated

Explained in chapter 3: if the ground truth were read from Neo4j, an error in
the database would show up on both sides and count as a hit. The ground truth
comes from the raw JSON and from layer 0, and it is **compared** with Neo4j,
never copied from it.

### No LLM grades anything

LLM judges make mistakes, vary from one run to another and cost money. With
closed questions and answers in a fixed format, grading is an `if`.

### The same setup in every arm

Within a round: same model, same instruction, temperature 0, same answer
format with the same number of retries. (Exceptions for temperature and
reasoning effort on the expensive models: 7.1, "Four models".) The format is
always delivered through the same PydanticAI mechanism (the answer comes as an
"output tool"), because it works together with the tools of `graph_tools`.
Using a different mechanism in some arm would be one more difference besides
the data.

The system instruction says the questions are about **one match**, without
saying which. Saying "the 2022 World Cup final" would help the model answer
from memory instead of using the data.

### Four models, paired by price

The first round used a single model, Claude Haiku 5.5. To find out whether the
order of the arms holds beyond it, three more were run, chosen in a 2 × 2
design: closed or open-weights, cheap or expensive.

| | Cheap tier | Expensive tier |
|---|---|---|
| **Closed** | Claude Haiku 5.5 (US$ 0.10 / 0.50 per million tokens) | Claude Sonnet 4.6 (US$ 3 / 15) |
| **Open weights** | Qwen3.8-flash (US$ 0.15 / 0.47) | Kimi K3 (US$ 3 / 15) |

The criterion is **price**, not size (which none of the closed labs discloses):
within each tier, the two models cost the same, and the question becomes "for
the same price, which form of data access pays off more?". Sonnet is not
Anthropic's top of the line (Opus is); it was the expensive closed model
available on the account used.

Accuracy on the 47 questions with an answer:

| Arm | Haiku 5.5 | Qwen3.8-flash | Sonnet 4.6 | Kimi K3 |
|---|---|---|---|---|
| `graph_tools` | 87% | 83% | 89% | 89% |
| `text_to_cypher` | 70% | 57% | 89% | 94% |
| `events_in_prompt` | 45% | 40% | 72% | 85% |
| `vector` | 11% | 9% | 15% | 17% |
| `stats_in_prompt` | 0% | 4% | 9% | 6% |
| `no_context` | 0% | 0% | 0% | 0% |

The reading: `graph_tools` stays between 83% and 89% on all of them. On the
cheap models, it is clearly the best; on the expensive ones, writing the query
(`text_to_cypher`) gets to the same place, and reading the whole table
(`events_in_prompt`) gets close, at a much higher cost in time and reasoning
tokens. Ready-made tools make a cheap model competitive with the expensive
ones.

The conditions of each round, which any write-up must state:

- **Haiku 5.5:** OpenRouter, temperature 0, no reasoning.
- **Qwen3.8-flash:** OpenRouter with the provider pinned to Alibaba, reasoning
  off (`none`), because Alibaba refuses structured output together with
  reasoning; temperature 0.
- **Kimi K3:** OpenRouter with the author's own Bedrock key (`us-east-2`), no
  fallback. It is a reasoning model and ran with reasoning on (the default).
  Bedrock does not accept `temperature` for it: it ran at the default
  temperature.
- **Sonnet 4.6:** Bedrock directly (`us-east-2`), extended thinking `medium`
  and temperature 1 (an Anthropic requirement with thinking). In
  `events_in_prompt`, with `medium`, the reasoning used up the 16 thousand
  token cap on 19 of the 52 questions, with no answer; the arm was rerun with
  `low`, and the 6 that still overflowed, with a 32 thousand cap. The result
  used is the combined file (`claude-sonnet-4.6_results.jsonl`), described on
  the run's page. On a sample of 5 questions, `medium` with 32 thousand got 3
  right and `low` with 16 thousand got 4: reasoning more did not help on this
  task.

Before each round, a 2-question screening showed whether the model worked. Left
out: DeepSeek V4 Pro (it failed to fill in the final answer or reasoned until
it hit the cap), GLM-5 (intermittent empty answers), gpt-oss-20b (the tool name
came out with an internal marker and Bedrock refused it) and the closed models
the account did not enable. That half of the models tested stumble on the
format of the calls is a finding in itself: the advantage of tools depends on
the model using them reliably.

The files and pages of each run are in `data/benchmark/` (one
`<model>_results.jsonl` and one `<model>_summary.md` per model) and in
[`docs/runs/`](runs/README.md).

### Questions without definitions, tested under every reading

The questions describe the concepts the way a commentator would ("the main
link in the ball circulation", "the pair that exchanged the most passes"),
without saying how to compute them. A test blocks tool or algorithm
vocabulary. The price is that the same question can be read in more than one
way. Instead of adding a definition to the text, the ground truth computes the
answer under every reasonable reading, and the question only stays if they all
agree (chapter 3, section 3.5).

### Primitive tools, frozen before the questions

The eight tools of `graph_tools` are operations with no ready-made tactical
concept: filter and count actions, list actions, count possessions, build a
passing network, compute a metric, list links, count sequences. The model has
to combine them. They were written and frozen before the questions that test
them, and a test keeps a hash of the definitions.

In `graph_tools`, the model never writes Cypher: each tool runs a fixed query,
with parameters. Writing queries would mix two skills (knowing how to query a
database and knowing how to use the data); `text_to_cypher` is the arm that
measures the first one. No tool reads the ready-made patterns of layer 2.

### Tool descriptions with the football reading

Each description has two parts: what the tool computes and what that usually
means in football ("betweenness... marks a player who connects teammates in
ball circulation"). A real product would do the same. It makes it easier for
the model to translate the question into the tool, and it is a deliberate
choice. The descriptions carry no rules made for a question, nor suggestions
of filters or weights for a concrete case.

### The `stats_in_prompt` sheet comes from Neo4j

Not from a separate computation. That way `stats_in_prompt` and `graph_tools`
start from the same database: the sheet is counted by Neo4j over the same
edges the tools query.

### The same event information in the three arms that see events

`events_in_prompt`, `vector` and `graph_tools`' `list_actions` show the same
facts about each action: period, minute, team, player, action, success,
receiver, zones, possession, outcome and score. The score appears in two ways:
**before** the action, on every row, and **after**, on a goal's row. The first
serves for slices ("while leading 2–0"); the second, for finding a goal by the
score it made ("the 2–2 goal"). None of the three receives ready-made counts.

### The `vector` arm indexes the same rows

Each row of the event table is a document. That way `vector` and
`events_in_prompt` see **the same material**, and the difference between them
is just "30 chosen rows" versus "all the rows". The embeddings are computed in
batches of 100 (about 26 requests) and cached.

### Prompt caching on the arms with fixed data

`events_in_prompt` sends the same ~100 thousand token table on every question,
and `stats_in_prompt` the same stat sheet. With prompt caching, the provider
stores that part on the first question and bills the following ones at a
fraction of the price (on Claude Haiku 5.5, reads at 10% of the input price).
In the sample without caching, `events_in_prompt` alone cost ~95% of the total.

For it to work, the message of those two arms goes in **two text blocks**: the
data, with the cache marker, and the question. The cache only reuses an
identical beginning, and the question changes every time. **The model reads
exactly the same text**; only the billing changes. That is why the project
uses PydanticAI's `OpenRouterModel` class, the only one that passes this
marker on to Anthropic models through OpenRouter. Models without this kind of
cache simply ignore it. `results.jsonl` records the tokens read from and
written to the cache (`cache_read_tokens`, `cache_write_tokens`).

Checked with Claude Haiku 5.5: the second `stats_in_prompt` question read
4,921 of 4,966 tokens from the cache and cost half.

### Provider errors do not become results

If the model's provider fails (server down, rate limit), after the SDK's own
retries, the run is reported and **not written**, and `--resume` redoes it. An
infrastructure failure is not a wrong answer from the arm. An answer that does
not fit the format, even after 2 retries, is written as a format error,
because that is the model's behavior.

### The script does not delete paid results without asking

If the results file already has runs, `run_benchmark.py` refuses to start and
asks for `--resume` (continue) or `--fresh` (start over). Results cost money;
deleting them must be an explicit decision.

---

## 7.2 Problems found in the data

Building the ground truth through an independent path serves to find
disagreements between the sources. The cases below are known and worked around
in the questions or in how the data is presented.

### Goalkeeper saves: 7 or 8?

The raw JSON has 7 saves by Hugo Lloris ("Shot Saved" events). Layer 0 has 8
save actions. The eighth, in minute 107, is actually the goalkeeper coming out
to clear the ball ("Keeper Sweeper Clear"), which the SPADL conversion
classified as a save. The graph's stat sheet inherits the 8.

**What was done:** no question uses goalkeeper saves. **What should be done
next:** fix the classification in layer 0.

### Attempted passes

The SPADL conversion drops some passes from the JSON: Enzo Fernandez has 94
attempted passes in the JSON and 92 in layer 0; Koundé, 67 and 66. **Completed**
passes match in both sources.

**How it is handled:** no question depends on attempted or missed passes; the
questions about passes use completed passes.

### The card recovered at the end of the table

Giroud's yellow card (95', for dissent) is not an on-ball action, so SPADL
drops it. Layer 0 recovers it from the raw JSON, but appends it **at the end of
the table**, with the last action number. Anyone reading the table in action
order would see the card after the last play of extra time.

**How it is handled:** the arms' event table and `list_actions` sort by period
and game time, not by action number. A test guarantees it.

### The database may hold other matches

If Neo4j was already used with other matches (earlier versions of the project
loaded three), their nodes are still there. Every benchmark query filters by
match (`match_id`), so this does not affect the results. For a clean database:
`docker compose down -v` and run the layers again.

---

## 7.3 Limitations: what the benchmark does not say

**One match, 52 questions.** 47 have an answer and 5 are controls. A question
is worth ~2 percentage points of the total, but 5 to 17 points within a group
(the smallest has 6 questions). The confidence intervals are wide (around ±12
points), and differences of a few questions between arms may be chance in the
questions chosen.

**Variation between runs.** At temperature 0, the same question can still get
different answers in different runs. With one repeat, the consistency table is
empty and that variation is not measured.

**It measures correctness, not quality.** The benchmark says whether the arm
got the name or the number right. It does not say whether it would explain a
play well, nor whether the reasoning (`rationale`) makes sense.

**Tools and questions by the same author.** The tools were frozen before the
questions, but they were designed by whoever wrote the questions. Later
presentation tweaks (the score in the events, network tool results that repeat
the filters, the player count in the sequences) were made after seeing model
errors on part of the questions. In real use, nobody guarantees that the right
tool exists.

**Descriptions that help.** The tool descriptions carry the tactical reading
of each metric (7.1). That brings the question closer to the tool.

**Questions that were removed.** 22 of the 81 questions written were removed
because the answer changed with the reading. Among them is "the main link in
the ball circulation" over the whole match, a common concept in football
analysis that, in this final, has no single answer.

**`graph_tools` mixes two effects:** having tools that compute and having graph
algorithms. Separating them requires an arm with only the action tools
(`list_players`, `query_actions`, `list_actions`), without the network ones.
That arm is one line of configuration (`TOOL_ARMS` in `arms.py`) and is left as
future work.

**`events_in_prompt` depends on a match fitting in the context.** The table is
~78 thousand to ~115 thousand tokens, depending on the model (240 thousand on
DeepSeek). A World Cup matchday or a league season does not fit, and the arm
would cease to exist; the tools would keep working.

**Four models, not a scaling curve.** With two cheap models and two expensive
ones, the benchmark shows that the order of the arms changes with the model
(7.1), but not at what point it changes. In the two expensive ones, size and
reasoning come together, and there is no way to separate one from the other
with this data. The choice of models depended on what the author's account
could use (Opus and GPT were not enabled). The model used is recorded on every
line of the results file.

**Different conditions in Sonnet 4.6's `events_in_prompt`.** That arm uses
reasoning effort `low` and, on 6 questions, a 32 thousand token cap; the other
arms of the same model use `medium` and 16 thousand (7.1). The comparison
between Sonnet's arms carries that difference.

**A tool fix after the Haiku round.** Reading arguments sent as JSON text
(chapter 4) came in after the Haiku round. Haiku never sent an argument that
way, so the fix should not change its numbers, but the round was not rerun to
prove it.

**Checking by set.** In the three-player sequences, the order is not checked.
In the question that compares the 1st and 2nd halves, only the 2nd half pair
is checked.

**The network ground truth depends on layer 0.** Networks and xT come from
layer 0, whose xT model was trained on games that include the final. The
ground truth and the graph start from the same Parquet, so the cross-check
validates layers 1 and 2 and the tools, **not layer 0**. That is why layer 0
has its own tests against the raw JSON.

**Fixed choices in `vector`.** 30 rows and one embedding model. Another number
of rows or another model would give another result; no variations were tested.

**Instructions in English, questions in Portuguese.** It is common in practice
and applies to every arm equally, but it is a variable that was not isolated.
