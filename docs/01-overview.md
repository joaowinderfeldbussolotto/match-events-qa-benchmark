# 1. Overview: what this project measures and why

## The question

Imagine you have the full record of a football match: every pass, every
shot, every foul, who did it, where and when. For the 2022 World Cup final
(Argentina vs France), that comes to about **4,400 events** in a JSON file
that StatsBomb provides for free.

Now someone wants to ask questions about the game in plain language:

- "Who gave the assist for France's second goal?"
- "Who made the most successful tackles?"
- "Which Argentina player did most passing routes go through?"

A language model (an LLM, like ChatGPT or Claude) understands the question,
but it did not watch the game. It has to receive the data somehow. The
question of this project is:

> **What is the best way to hand this data to the model so that it answers
> correctly?**

There are four common ways to do it, and the benchmark compares them, plus a
control with no data at all and a sixth way in which the model writes its own
database queries. Each way is called an **arm** (as in the arms of a
scientific experiment: groups that receive different treatments and are
compared with each other).

The questions themselves are in Portuguese, as the benchmark was built and run
in Portuguese; the examples in this documentation are translated.

## The six arms, explained with an analogy

Think of a journalist who has to answer questions about the game. The arms are
six journalists who get different material:

| Arm | The journalist gets... | In practice, the model gets... |
|---|---|---|
| `no_context` | nothing; answers from memory | only the question |
| `vector` | the 30 index cards from the archive that look most like the question | the 30 lines of the event table whose text is most similar to the question |
| `events_in_prompt` | the whole match file, play by play | a table with all 2,585 actions of the match (~80 to 115 thousand tokens, depending on the model) |
| `stats_in_prompt` | the ready-made stat sheet | a table with the statistics of each player and each team |
| `graph_tools` | an analyst with a database, who can be asked up to 12 queries | tools that query a graph database |
| `text_to_cypher` | the database and its blueprint; writes its own queries | the graph schema and a tool that runs, read-only, the Cypher query it writes |

A few details that matter:

- **`no_context` is the control.** It shows what the model "knows from
  memory". Since the 2022 final is famous, the model probably knows Messi
  scored the first goal. This arm separates what comes from the data from what
  comes from memory.
- **`vector` is the most common approach today** (called vector RAG). Each
  line of the table becomes a vector of numbers that stands for the "meaning"
  of the text, and so does the question. The lines whose vectors look most
  like the question's go to the model. It is fast and cheap, but it only
  brings pieces.
- **`events_in_prompt` is brute force.** Everything goes to the model, which
  has to count and cross-reference on its own, reading thousands of lines.
- **`stats_in_prompt` hands over work already done**: ready-made counts per
  player and per team. It answers well what was precomputed and cannot answer
  what was not.
- **`graph_tools` lets the model investigate.** It gets tools like "rank a
  statistic" or "who connects the team's passing network" and decides which to
  call, with which arguments, until it has the answer.
- **`text_to_cypher` lets the model write the investigation itself**: instead
  of ready tools, it gets the graph's blueprint and writes the queries.

**The only difference between the arms is what the model receives.** Within a
round, the model is the same, the instructions are the same, the temperature
is zero (the model always picks the most likely answer, without sampling) and
the answer format is the same. If an arm gets more right, it is because of the
data it received. The benchmark was run on four models, each in a round of its
own (below).

## The 52 questions, in five groups

There are 52 questions, of ten types, gathered in five groups. The groups exist
because each arm should do well on some and badly on others, and the
interesting part is to see where each one breaks.

| Group | Questions | What it takes | Real example from the benchmark | Answer |
|---|---|---|---|---|
| Search and counting | 11 | finding an event, or filtering, counting and ranking within a slice of the game | "While Argentina was leading 2–0, which Argentina player completed the most passes, and how many?" | Enzo Fernández, 26 |
| Pass network relations | 20 | a network concept (pair, link, sequence of three), over the match or a slice of it, and "if so-and-so were not on the pitch" | "If Enzo Fernández were not on the pitch, who would become the main link in Argentina's ball circulation?" | Otamendi |
| Plays and sequences | 10 | whole plays (where they start, where they get to, who takes part) and what comes right before an action | "Which two Argentina players most often took part together in the same plays that reached the final third?" | Enzo Fernández and Messi |
| Before and after a game moment | 6 | finding a substitution and comparing the ball circulation after it | "After Di María was substituted, which teammate passed the ball to Messi the most?" | Enzo Fernández |
| Control: no answer | 5 | noticing that the data does not exist | "How many minutes did Messi spend in the attacking half during the final?" | `no_data` |

Why each group is hard:

- **Search and counting**: sometimes finding the right line is enough, but it
  has to be found, often relative to another moment ("the foul that led to the
  penalty"); in aggregations, the slice has to be located ("while leading
  2–0") and dozens of events counted inside it without mistakes.
- **Pass network relations**: the answer is not on any line nor in any simple
  count. It comes from looking at the whole passing network (who passes to
  whom), sometimes over a piece of the game, sometimes without one player.
- **Plays and sequences**: the actions have to be grouped into plays
  (possessions), or the exact order of the passes has to be read.
- **Before and after**: the moment of the substitution has to be found first,
  and only then counted from.
- **Control**: the right answer is "I do not have this data". The questions
  look answerable from events, but they ask for something only continuous
  player tracking would have (time in each part of the pitch, speed,
  distance). The typical mistake is to approximate with another measure, such
  as counting carries instead of sprints.

The questions are worded like a commentator would put them and do not say how
to compute the answer. So that this does not create ambiguity, every right
answer is computed under every reasonable reading of the question, and only
the questions on which all readings agree are kept (chapter 3).

## How we know an answer is right

Each question has a **ground truth** (the right answer), computed by code from
the raw data, **without using the database the arms query**. That way the
ground truth does not inherit a possible error of the system under test. The
ground truth is also checked against the database through the `graph_tools`
tools: all 52 answers agree.

Each answer from the model is checked **by code, not by another model**. The
model answers in a fixed format (a list of players, a number, or "no data")
and a program compares it with the ground truth. There is no "half right" and
no opinion: it is right or wrong. Details in
[chapter 5](05-scoring-and-metrics.md).

## What comes out at the end

After running the 52 questions through the 6 arms (with one or more repeats),
the project writes a summary (`summary.md`) and a run page in
[`docs/runs/`](runs/README.md) with:

1. **accuracy by question group and by arm**, the main table, with the total
   with and without the questions that have no answer;
2. **kinds of error by arm**: hallucination (a wrong answer given with
   confidence), abstention (said "no data" when there was data) and format
   error;
3. **consistency**: whether the same arm gives the same answer across repeats;
4. **cost**: average tokens and time per question.

## Four models

The comparison was run on four models, in a 2 × 2 design: closed or
open-weight, cheap or expensive (the two in each price band cost the same).

| Arm | Claude Haiku 5.5 (cheap, closed) | Qwen3.8-flash (cheap, open) | Claude Sonnet 4.6 (expensive, closed) | Kimi K3 (expensive, open) |
|---|---|---|---|---|
| `graph_tools` | 87% | 83% | 89% | 89% |
| `text_to_cypher` | 70% | 57% | 89% | 94% |
| `events_in_prompt` | 45% | 40% | 72% | 85% |

Accuracy on the 47 questions that have an answer. The ready-made tools score
the same on every model; on the cheap ones they are clearly the best approach,
and on the expensive ones the other two get close, at a higher cost in time
and tokens. The details, the conditions of each round and the limits of this
reading are in [chapter 7](07-decisions-and-limitations.md).

## Map of the documentation

| Chapter | What it explains |
|---|---|
| 1. Overview | this text |
| [2. From the data to the graph](02-from-data-to-graph.md) | the path from the raw JSON to the database, following Di María's goal |
| [3. Questions and ground truth](03-questions-and-ground-truth.md) | how the questions are written (the YAML file) and how the right answer is computed and checked |
| [4. The six arms](04-the-six-arms.md) | exactly what each arm sends to the model, with real excerpts |
| [5. Scoring and metrics](05-scoring-and-metrics.md) | how each answer is scored and how to read `summary.md` |
| [6. How to run](06-how-to-run.md) | step by step from scratch, on your computer or in Docker, with expected outputs and troubleshooting |
| [7. Decisions and limitations](07-decisions-and-limitations.md) | the choices made, the problems found in the data and what the benchmark does not measure |
| [8. Glossary](08-glossary.md) | every technical term, in plain language |
| [9. Data transformations](09-data-transformations.md) | everything that happens to the data, from the raw JSON to what each arm sees, and how the ground truth is computed |

If this is your first time here, read in order. If you only want to run it, go
straight to [chapter 6](06-how-to-run.md).

A Portuguese version of every chapter is in [`docs/pt-br/`](pt-br/01-visao-geral.md).
