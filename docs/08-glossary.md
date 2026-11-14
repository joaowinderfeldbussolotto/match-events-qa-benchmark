# 8. Glossary

Terms used in the documentation and in the code, in alphabetical order,
explained without assuming prior knowledge. Where the code or the Portuguese
docs use a Portuguese word, it is given in parentheses.

---

**Abstention.** When the model answers "I have no data for that" (`no_data`)
on a question that had an answer. It counts as an error, but it is recorded
apart from hallucination, because it is an honest error (chapter 5).

**Agent.** A language model that can use tools: it decides which one to call,
reads the result and decides the next step. In the benchmark, the
`graph_tools` and `text_to_cypher` arms are agents.

**Arm (braço).** Each of the six ways of giving data to the model
(`no_context`, `vector`, `events_in_prompt`, `stats_in_prompt`, `graph_tools`
and `text_to_cypher`). The name comes from scientific experiments, in which
each arm is a group with a different treatment.

**Benchmark.** A standardized test to compare alternatives under the same
conditions. Here, to compare six ways of giving data to a model.

**Betweenness centrality.** For each pair of players in the team, the shortest
passing path between them is found, and whoever sits in the middle of that
path is counted. The more paths go through a player, the higher their
betweenness. It is a measure of "who connects the team". It is not the same as
making more passes (chapter 3, with an example).

**Bridge.** A link in the passing network that, if removed, splits the team
into two groups with no connection. The final had none.

**BYOK (bring your own key).** Registering a provider's key on OpenRouter
(here, Amazon Bedrock's): the calls pinned to that provider are billed on its
account, not on the OpenRouter balance.

**Carry (conducao).** Moving with the ball under control. In the SPADL format
it is called `dribble`, which is confusing; in layer 0 it becomes `conducao`.

**Community (Louvain).** A group of players who exchange passes mostly among
themselves. The Louvain algorithm finds these groups, but with a random
component: the groups may change from one run to another.

**Context (context window).** The maximum amount of text, in tokens, that a
model can read at once. The `events_in_prompt` arm needs about 78 to 115
thousand tokens, depending on the model's tokenizer.

**Cosine similarity.** A measure, from -1 to 1, of how much two vectors point
in the same direction. Used to find the event rows most similar to the
question.

**Cypher.** Neo4j's query language. It describes paths in the graph:
`(a:Jogador)-[:PASSOU_PARA]->(b:Jogador)`.

**Deterministic.** Always giving the same result for the same input. Layers 0
to 2 and the scoring of the answers are deterministic; an LLM is not
guaranteed to be.

**Edge.** In a graph, a link between two nodes. Example: `PASSOU_PARA`
("passed to") links the player who passed to the one who received.

**Embedding.** A list of numbers (a vector) that represents the meaning of a
text. Similar texts have similar vectors. It is the basis of the `vector` arm.

**Field tilt.** A team's share of the passes made in the attacking third,
adding up both teams. It measures territorial dominance: 54% (Argentina in the
final) means that, of all the passes made in the opponent's final third by
both teams, 54% were Argentina's. 50% is balance.

**GDS (Graph Data Science).** A Neo4j library with ready-made graph algorithms
(betweenness, Louvain, bridges...).

**Graph.** A way of storing data as nodes (things) and edges (links). Good for
questions about relationships.

**Ground truth (gabarito).** The right answer to each question, computed by
code from the raw data (chapter 3). It lives in
`data/benchmark/ground_truth.json`.

**Hallucination.** When the model gives a wrong answer as if it were right. On
questions with no answer in the data, any answer other than "no data" is a
hallucination.

**Inference profile.** On Bedrock, an identifier that routes a model's call to
one or more regions (prefix `us.` or `global.`, as in
`us.anthropic.claude-sonnet-4-6`). Several models only accept being called
through one.

**JSON / JSON Lines.** JSON is a text format for structured data. JSON Lines
(`.jsonl`) has one JSON object per line; it is the format of `results.jsonl`,
which allows writing one run at a time.

**Langfuse.** A service that shows, step by step, each conversation with the
model. Optional; it is for investigating errors, not for measuring.

**Layer (camada).** Each stage of the data processing: 0 (action table), 1
(factual graph), 1b (stat sheet), 2 (network patterns). Chapter 2.

**LLM (Large Language Model).** A large language model, such as ChatGPT,
Claude or Gemini. It reads and writes text.

**Model provider.** The company that runs the model and charges for it. The
same open-weights model can be served by several providers, with different
prices and quantizations; that is why the provider is pinned in each round
(`LLM_PROVIDER_ORDER`).

**Neo4j.** The graph database used in the project.

**networkx.** A Python graph library, used to recompute the passing network
independently of Neo4j, in the ground truth.

**Node.** In a graph, a "thing": a player, a team, a zone of the pitch.

**Open weights.** A model whose parameters are published: anyone can download
and run it, and the version does not change without notice. Here,
Qwen3.8-flash and Kimi K3. It is not the same as open source.

**Output cap.** The maximum number of tokens the model may write in one call
(`LLM_MAX_TOKENS`, 16 thousand in the benchmark). In a reasoning model, if the
reasoning uses up the whole cap, no answer comes out and the run counts as a
format error.

**Parquet.** A compact, fast table file format. Layer 0 writes the action
table in Parquet.

**Possession (by time).** The percentage of time each team had the ball,
adding up the length of the possession phases. It is not the share of
touches, which would favor whoever touches the ball a lot.

**Possession phase.** A run of consecutive actions by the same team with the
ball, until it loses it or play stops. The final had 537.

**PPDA (Passes Per Defensive Action).** How many passes the opponent makes, on
average, before the team makes a defensive action (tackle, interception,
foul). **The lower it is, the more the team presses.**

**Prompt.** The text sent to the model: system instruction, data (when the arm
sends it) and question.

**Prompt caching.** The provider stores the beginning of a prompt already sent
and bills re-reading it at a fraction of the price. It helps when many
questions start with the same long text, such as the event table. The model
reads the same text; only the bill changes.

**PydanticAI.** The Python library the project uses to talk to the models,
define tools and enforce the answer format.

**RAG (Retrieval-Augmented Generation).** Finding relevant passages in a
collection and giving them to the model together with the question. The
`vector` arm is vector RAG.

**Reasoning (reasoning model).** A model that writes internal reasoning before
the answer. The reasoning counts as output: it costs and takes up the output
cap. The **effort** (`LLM_REASONING_EFFORT`: `none`, `low`, `medium`, `high`)
controls how much it reasons.

**SPADL.** A standardized format for football actions: one row per on-ball
action, with the same fields for every kind of action, and the pitch flipped so
that every team attacks from left to right.

**Stat sheet (súmula, layer 1b).** The precomputed stats of each player and
each team (passes, tackles, goals...), stored in Neo4j.

**StatsBomb Open Data.** Free match data published by the company StatsBomb,
including the 2022 World Cup.

**Structured output.** Forcing the model to answer by filling fixed fields
(here: `rationale`, `players`, `value`, `no_data`), instead of free text.

**Tackle won / attempted (desarme certo / tentado).** Attempted: the player
tried to take the ball from the opponent. Won: they succeeded. Enzo Fernandez
attempted 9 and won 5 in the final.

**Take-on (drible).** An attempt to beat the marker with the ball. In SPADL it
is called `take_on`.

**Temperature.** A model setting that controls how much it "samples" the
words. At 0, it always picks the most likely one.

**Third of the pitch (terço).** The pitch split into three bands along its
length: defense, middle and attack.

**Token.** The piece of text the model reads and writes, usually a short word
or part of a word. Providers bill per token.

**Tool calling.** The model's ability to ask the program to run a function (a
"tool") and to use the result.

**VAEP (Valuing Actions by Estimating Probabilities).** Measures the value of
each action by the change in the chance of scoring **and** of conceding soon
after. It is computed by a model trained on World Cup games.

**xT (expected threat).** Each zone of the pitch has a value that indicates the
chance of that possession becoming a goal. Moving the ball from a weak zone to
a strong one generates positive xT. Mac Allister's pass to Di María, in the
36' goal, generated 0.184.

**Zone (zona).** One of the 96 cells of the 12 × 8 grid the pitch is divided
into. Column 0 is next to the team's own goal; column 11, next to the
opponent's goal.
