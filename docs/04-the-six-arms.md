# 4. The six arms, inside

This chapter shows **exactly** what each arm sends to the model, with real
excerpts. The code is in `src/football_graphrag/benchmark/arms.py` (arms) and
`benchmark/tools.py` (the `graph_tools` tools). The full list of
transformations, column by column, is in [chapter 9](09-data-transformations.md).

Everything the model receives is shown as it is sent: the system prompt, the
tool descriptions and the data legends are in English, while the questions and
the data labels (action types, graph labels, stat names) are in Portuguese
(chapter 2 explains them).

---

## 4.1 What all arms have in common

For the comparison to be fair, only one thing may change: **the data the model
receives**. Everything else is the same:

| Item | Value | Why |
|---|---|---|
| Model | the one in `.env` (`LLM_PROVIDER` + `LLM_MODEL`) | the same "brain" in every arm of a round; each model evaluated is a round of its own (chapter 7) |
| Temperature | 0 | the model always picks the most likely answer, without sampling; reduces variation between repeats. Exceptions: with extended thinking on Bedrock (Sonnet 4.6), Anthropic requires 1, and Kimi K3 on Bedrock does not accept the parameter and runs at its default temperature |
| System prompt | the same for all (below) | the same rules of the game |
| Answer format | the `Answer` model (chapter 5); an empty answer is refused | the same scoring for all |
| Format retries | up to 2 new attempts if the answer does not fit the format | the same tolerance for all |

The **system prompt** (the text the model receives before any question) is
this:

```text
You answer questions about one football match, using the data provided in
this conversation. Questions are in Portuguese.

Answer only with the data provided in this conversation (in the message or
returned by your tools). Do not use outside knowledge, even if you think you
know the answer. If the provided data does not contain exactly what the
question asks for, set no_data to true: do not answer with a different or
approximate measure in its place.

Write player names exactly as they appear in the data.
```

The prompt does not say **which** match it is: only that the questions are
about one match, the one in the data. That way the prompt does not help the
model answer from memory. (The questions and the data still make it possible to
recognize the game; the rule below is what forbids using memory.)

The last part ("do not answer with a different or approximate measure in its
place") is there because, without it, models tend to replace what was asked
with something similar that the data has, such as counting carries when the
question is about high-speed sprints.

This prompt has a consequence for the `no_context` arm: since it receives no
data at all, **the right behavior is to answer `no_data` to almost
everything**. If it gets "who scored the first goal" right, it used memory and
disobeyed the prompt.

### Size of each arm

Input tokens per question (average of a full run with Claude Haiku 5.5;
tokens are the unit providers bill by):

| Arm | Tokens | What weighs |
|---|---|---|
| `no_context` | ~900 | prompt + answer format + question |
| `vector` | ~2,600 | + 30 event lines with the legend |
| `stats_in_prompt` | ~5,000 | + full stat sheet with glossary |
| `graph_tools` | ~76,000 | description of the 8 tools, repeated at every call, plus the results |
| `events_in_prompt` | ~111,000 | + all 2,585 actions; with prompt caching, only the first question pays full price |

`events_in_prompt` needs a model with a context window of at least 128
thousand tokens.

The token count depends on each model's tokenizer. The same event table
measured on other models: ~78 thousand (gpt-oss), ~82 thousand (Kimi K3), ~90
thousand (Sonnet 4.6), ~91 thousand (Qwen3.8-flash) and ~240 thousand (DeepSeek
V4, which therefore needs a much larger context).

---

## 4.2 `no_context`: only the question

The model receives the system prompt and the question, nothing else.

**What to expect:** answering "no data". It serves as a baseline: it measures
how much the model answers from memory.

---

## 4.3 `events_in_prompt`: the whole game, play by play

The model receives a table with **one row per action**, all 2,585 of them, in
match order, preceded by a legend:

```text
Match events:
One row per on-ball action (SPADL), in match order; penalty shootout excluded.
period: 1 and 2 regular time, 3 and 4 extra time. minute: broadcast minute (stoppage
time continues the count, so the 1st half goes past 45). team, player: who acted. action: action type
(Portuguese labels, e.g. passe, conducao, drible, desarme, interceptacao,
falta_cometida, finalizacao, penalti, cartao_por_reclamacao). success: 1/0.
receiver: who received a completed pass. zone_from/zone_to: cell of a 12x8 grid,
zone = column*8 + row, column 0-11 from the acting team's own goal to the
opponent's goal; third = zone // 32 (0 defensive, 1 middle, 2 attacking).
possession: id of the possession phase. outcome: goal with the score it made,
e.g. goal(3-2), yellow_card, and the shot result (defendida, bloqueada,
para_fora) when there is one. score: the score Argentina-France when the
action starts, before it (2-1: Argentina 2, France 1).

period,minute,team,player,action,success,receiver,zone_from,zone_to,possession,outcome,score
1,1,France,Antoine Griezmann,passe,1,Aurélien Djani Tchouaméni,51,35,1,,0-0
1,1,France,Aurélien Djani Tchouaméni,conducao,1,,35,35,1,,0-0
...
4,124,Argentina,Paulo Bruno Exequiel Dybala,corte,1,,10,10,537,,3-3

Question: <the question>
```

The end of Di María's goal sequence (chapter 2) shows like this:

```text
1,36,Argentina,Alexis Mac Allister,passe,1,Ángel Fabián Di María Hernández,74,92,132,,1-0
1,36,Argentina,Ángel Fabián Di María Hernández,finalizacao,1,,92,91,132,goal(2-0),1-0
```

Each column is a layer 0 value, with no ready-made count. Some exist so that the
arm has the facts the questions use:

- **`period`:** the broadcast minute repeats between halves (the final's first
  half ran to 53', and the second restarts at 46'). Without the period, "52'"
  is ambiguous.
- **`possession`:** tells whether two passes were in the same play.
- **`outcome`:** marks a goal, with the score it made, a yellow card and the
  result of shots.
- **`score`:** the score when the action starts. It allows locating slices
  like "while leading 2–0" without rebuilding the score in one's head.

**What to expect:** all the facts are there, but the model has to **count and
cross-reference on its own**, reading 111 thousand tokens. Isolated facts tend
to go well. Long counts and network computations are where it tends to fail or
give up.

---

## 4.4 `vector`: the 30 most similar lines

This is "vector RAG", the most common way to connect an LLM to documents.

**How it works, step by step:**

1. **Preparation (once).** Each of the 2,585 lines of the event table is sent
   to an *embedding* model, which returns a vector: a list of hundreds of
   numbers that stands for the "meaning" of the text. Similar texts get similar
   vectors. The vectors are stored in `data/benchmark/cache/` and are not paid
   for again as long as the table does not change.
2. **At each question**, the question also becomes a vector.
3. The **cosine similarity** between the question's vector and each line's is
   computed. It is a number from -1 to 1 that measures how much two vectors
   point in the same direction.
4. The **30 most similar lines** go to the model, put back in match order, with
   the same legend as `events_in_prompt`.

There is no vector database: the vectors sit in an in-memory matrix (numpy)
and the search is a matrix multiplication.

**What to expect:** good when the answer is in **one or a few lines** with
words similar to the question's. Bad for counts ("how many passes?" needs every
pass line, not 30) and for network questions. The similarity is of **text**,
not of football meaning.

---

## 4.5 `stats_in_prompt`: the ready-made stat sheet

The model receives the layer 1b stat sheet (chapter 2), **read from Neo4j**:
first a glossary of each column, then one row per team and one per player.

```text
Match stats:
What each column means:
- acoes: on-ball actions of any type (team)
- acoes_no_terco_final: actions in the attacking third (team)
- assistencias: passes that set up a goal
- desarmes_certos: tackles won
...

Team stats:
nome,acoes,acoes_no_terco_final,cartoes_amarelos,desarmes_certos,...,posse_pct,...

Player stats (one row per player who acted):
nome,time,posicao,assistencias,cartoes_amarelos,conducoes,cortes,...

Question: <the question>
```

**What to expect:** good when the question is about the whole match and the
count is already done. The sheet has no time slices (a half, extra time, "after
2–2"), nor who passed to whom, nor the order of the plays. In those cases, the
right answer is "no data".

---

## 4.6 `graph_tools`: the model investigates with tools

Here the model **receives no data**. It receives the question and a list of
tools, each with a name, a description and arguments. The model decides which
one to call; the program runs the tool (a query to Neo4j) and returns the
result; the model reads it and decides whether to call another or answer. This
is called *tool calling*.

### The eight tools

They are **primitives**: none carries a ready-made tactical concept. The model
has to combine them.

| Tool | What it does |
|---|---|
| `list_players` | lists the players, with team and position |
| `query_actions` | counts actions (or adds up their xT) with filters, grouping by player, receiver, team, action, period, third or corridor |
| `list_actions` | lists actions in order, with the second of the game, the score before the action and, for a goal, the score after |
| `query_possessions` | counts a team's plays (possessions) with filters on where they start, where they get to, how they end and who takes part; groups by player or by pair |
| `pass_network` | builds a team's passing network, with filters; returns an identifier |
| `network_metric` | computes a metric over the network: betweenness, degree, PageRank, bridges, articulation points or communities |
| `network_edges` | lists the network's links (who passed to whom, how many times) |
| `pass_paths` | counts the most repeated sequences of players in chained passes (A → B → C) |

The filters are the same in all of them: team, player, action type, success or
failure, period, time window in seconds, third, corridor, goal, card, assist.
The rules of each filter and each metric are in
[chapter 9](09-data-transformations.md#the-graph_tools-tools).

### An example of the loop

Question: "In extra time, who was the main link in France's ball circulation?"
(real trace, trimmed):

1. `pass_network(team="France", filters={"period": [3, 4]})` returns
   `{"network_id": "net1", "team": "France", "filters": {"period": [3, 4]}, "players": ..., "passes": ...}`.
2. `network_metric(network_id="net1", metric="betweenness", weight="passes", direction="undirected")`
   returns Koundé first, well ahead of Tchouaméni and Varane.
3. The model answers `players: ["Jules Koundé"]`.

### How the tools were designed

- **Fixed queries.** Each tool runs a hand-written Cypher query, with
  parameters. The model **never writes Cypher**.
- **A two-part description.** Each description says what the tool computes
  (mechanics) and what that usually means in football, with no rules made for
  a specific question. Example, from betweenness: "for every pair of other
  players, counts how many shortest passing routes go through each player... In
  football terms, betweenness marks a player who connects teammates in ball
  circulation, a link or hub of the build-up".
- **None reads layer 2.** The already computed patterns (`PadraoTatico`) would
  be the answer handed over. The network metrics are computed **on the spot**.
- **Results that explain themselves.** Every network tool repeats the team and
  the filters the network was built with, so the model does not mix up two
  networks.
- **Errors become messages.** A team that does not exist, an ambiguous name
  ("Martínez" is Lautaro or Emiliano?) or a network not created yet produce a
  message explaining the problem, and the model can try again.
- **Tolerant about format, not about content.** Before validation, each
  argument goes through a cleanup: stray quotes around a string (`'"France"'`)
  are dropped, and an object or list sent as JSON text
  (`"{\"yellow_card\": true}"`, as Qwen and MiMo do) becomes the object. The
  result still goes through the argument's validation: an invented key or a
  value outside the allowed list is still refused. The second cleanup came
  after the Haiku round, which never sent an argument in that form (chapter 7).
- **One call at a time, up to 12 per question.** From the 13th on, the tool
  answers "limit reached, answer with what you have". If the model still
  insists, the run stops after 16 requests to the provider and counts as a
  format error.
- **Frozen before the questions.** The tools and their descriptions are fixed
  before the questions that test them are written. `tests/test_tools_frozen.py`
  stores a hash of the definitions.

**What to expect:** it is the only arm able to compute networks and slices
without reading everything, so it should do better on aggregations and network
questions. The risk is in picking the wrong tool, misreading the result or
misplacing the moment of the game.

---

## 4.7 `text_to_cypher`: the model writes the queries

The sixth arm. In the code it is optional (it only runs when listed in `--arms`
or in `config/benchmark.yaml`), but every published round includes it. It is
the *text-to-Cypher* pattern: instead of ready-made tools, the model receives
the **graph's blueprint** and **a single tool**, `run_cypher`, which runs the
query it writes. Every count, network or sequence is its own query. Code:
`benchmark/cypher.py`.

**What the model receives:**

- the question, after the graph **schema**, read from Neo4j itself (not written
  by hand): node labels, edge types, how many there are in this match, each
  property with its type and range of values, and the full list of the small
  vocabularies (`acao`, `terco`, `corredor`...). A short line says what each node
  and edge is for, and what the less obvious properties mean (continuous
  `segundo`, `periodo` 3 and 4 = extra time, `zona` in the 12x8 grid). It is ~11
  thousand characters, the same at every question, so it is cached like in
  `events_in_prompt`;
- the graph holds three matches: the schema says which `match_id` is the one of
  the questions (a number, not the name of the game), and the model has to
  filter by it.

**What the tool does and refuses:**

| Protection | How |
|---|---|
| Read only | a filter refuses `CREATE`, `MERGE`, `SET`, `DELETE` and so on; and the query runs in a read session, where Neo4j itself refuses writes |
| No procedures | `CALL db.*`, `gds.*` and `apoc.*` are refused (`CALL { ... }` subqueries are allowed). Without the algorithm library, betweenness and the like have to be written in Cypher |
| No ready-made answers | the `PadraoTatico` nodes (layer 2 findings, such as "Koundé is France's bottleneck") are left out of the schema, and a query that mentions them is refused |
| Size | up to 50 rows per query (with a truncation notice) and 15 s per query |
| Errors | a syntax error comes back as a message, for the model to fix |

The limit of 12 calls is the same as `graph_tools`.

**Can the graph answer all of this?** Yes. `scripts/check_cypher.py` answers
the 47 questions that have an answer with a hand-written Cypher query for each
one, through the same tool (same filter, read session, row limit), and agrees
with the ground truth on all 47, with no LLM and no cost. Even the "main link"
ones fit in a query: all shortest paths between two teammates and the share of
them in which each player sits in the middle. So what this arm measures is
whether the model **writes** these queries, not whether the data exists.

To run it (it spends credits):

```bash
python scripts/ask.py --question n11 --arm text_to_cypher
python scripts/run_benchmark.py --arms text_to_cypher --repeats 1 \
    --output data/benchmark/text_to_cypher_results.jsonl --title "text_to_cypher"
```

## 4.8 Running a single arm

To watch all of this happen, without writing results:

```bash
python scripts/ask.py --question s01 --arm graph_tools
python scripts/ask.py --question a01 --arm stats_in_prompt --show-prompt
```

`--show-prompt` prints the full prompt sent. For `graph_tools`, the output lists
each tool called, with its arguments. Details in [chapter 6](06-how-to-run.md).
