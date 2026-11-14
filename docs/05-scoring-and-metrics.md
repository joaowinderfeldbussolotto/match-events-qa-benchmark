# 5. Scoring and metrics: how each answer is graded

**No LLM grades anything in this benchmark.** All grading is done by code,
comparing the model's answer with the ground truth. This chapter explains the
answer format, the scoring rules, the kinds of error and how to read the final
report. The code is in `src/football_graphrag/benchmark/scoring.py`.

---

## 5.1 The answer format: the `Answer` model

If each model answered in free text ("I think it was Enzo, with about 5
tackles..."), the text would have to be interpreted, and interpretation makes
mistakes. So every arm answers in a **fixed format**, called structured
output: the model must fill four fields.

```python
class Answer(BaseModel):
    rationale: str        # the reasoning, written BEFORE the answer
    players: list[str]    # player names; rankings in order
    value: float | None   # one number, no unit
    no_data: bool         # True only if the data does not answer
```

| Field | What the model fills in | Example (question a05) |
|---|---|---|
| `rationale` | a short reasoning, based on the data | "2–0 runs from Di María's goal (36') to Mbappé's penalty (80'); in that stretch, Enzo Fernandez completed 26 passes." |
| `players` | full names; in rankings, from best to worst | `["Enzo Fernandez"]` |
| `value` | a single number, without "passes" or "%" | `26` |
| `no_data` | `true` only if the data does not allow an answer | `false` |

**Why does `rationale` come first?** A language model writes one piece at a
time, in the order of the fields. With the reasoning before the answer, it
"thinks" before answering, which tends to improve accuracy. The `rationale` is
**never graded**: it exists to investigate errors (to understand *why* an arm
got it wrong).

Each field has a short description, in English, that the model reads. It is
part of the contract: it says how to write names ("full player names as they
appear in the data") and numbers ("a single number, no units").

**What if the model does not follow the format?** PydanticAI (the library that
talks to the model) detects it, sends the error back to the model and asks
again, up to **2 times**. If it still does not fit the format, the run is
recorded as a **format error** and the benchmark moves on to the next one.

**An empty answer does not count.** An answer with no player, no number and no
`no_data` says nothing. The format refuses it, and it goes back to the model
like any other answer that does not fit the format. If it persists, it is a
format error, not a hallucination.

---

## 5.2 The scoring rules

Each question says in the YAML how it is checked (the `check` field, chapter
3). The rules, with real examples:

### `player`: the first name must be the expected one

Question f04, "Who made the pass for the goal that made it 2–2 in regular
time?". Ground truth: Marcus Thuram.

| Model answer | Result | Why |
|---|---|---|
| `players: ["Marcus Thuram"]` | ✅ right | |
| `players: ["Thuram"]` | ✅ right | surname unique in the match (5.3) |
| `players: ["Kylian Mbappé", "Marcus Thuram"]` | ❌ wrong | only the **first** counts, and the first is the goal scorer |
| `players: []`, with no number and no `no_data` | ⚠️ refused by the format | after 2 retries, format error |

### `value`: the number must match

Question a03, "After the goal that made it 2–2 in regular time, how many shots
did Argentina take until the end of extra time?". Ground truth: 10.

| Answer | Result |
|---|---|
| `value: 10` or `value: 10.0` | ✅ right |
| `value: 12` | ❌ wrong |
| `value: null`, with a player | ❌ wrong |

Counts are **exact**. The YAML allows a margin (`tolerance`) for continuous
numbers, such as percentages, but no current question uses it.

### `set`: the set of players, in any order

Question n04, "Which French pair exchanged the most passes with each other in
the final?". Ground truth: Upamecano and Varane.

| Answer | Result | Why |
|---|---|---|
| `["Varane", "Upamecano"]` | ✅ right | order does not matter |
| `["Varane"]` | ❌ wrong | one is missing |
| `["Varane", "Upamecano", "Koundé"]` | ❌ wrong | one too many |

In the three-player sequences (n09, s07), the check is also by set: the three
right names, in any order.

### `player_and_value`: both things

Question a05, "While Argentina led 2–0, which Argentine player completed the
most passes, and how many?". Ground truth: Enzo Fernandez, 26.

| Answer | Result |
|---|---|
| `["Enzo Fernández"], 26` | ✅ right (the accent does not matter) |
| `["Enzo Fernández"], 51` | ❌ wrong (51 counts from kick-off) |
| `["Otamendi"], 26` | ❌ wrong |

### `no_data`: saying there is no data

Question u03, "How many high-speed sprints did Mbappé make in extra time?".
Ground truth: `no_data`.

| Answer | Result |
|---|---|
| `no_data: true` | ✅ right |
| `value: 7` | ❌ wrong, and counts as a **hallucination**: the data has no running speed; 7 is the number of carries, another measure |

---

### Ties: more than one right answer

Sometimes two players tie for the right answer (in p07, Rabiot and Tchouaméni
took part together in as many plays as Rabiot and Mbappé). The ground truth
keeps the equally right forms in the `accepted` field, and the scoring accepts
**any of them**, or **all the tied ones together** (the model that answers "the
two are tied" is also right). A tie does not remove a question from the
benchmark; only a question whose answer changes from one reading to another is
removed (chapter 3).

## 5.3 Names: how "Messi" becomes "Lionel Andrés Messi Cuccittini"

The data uses the full registered name. The model may write "Messi", "Lionel
Messi" or "messi". To avoid penalizing that, the scoring uses an **alias
dictionary** built automatically from the StatsBomb lineups:

1. the **full name** (`player_name`): "Lionel Andrés Messi Cuccittini";
2. the **official nickname** (`player_nickname`): "Lionel Messi";
3. the **surname alone, only when it is unique in the match**: "Messi".

And every comparison **ignores accents, case and comments in parentheses**:
"Enzo Fernández", "ENZO FERNANDEZ" and "Enzo Fernandez (ARG)" are the same
name.

Rule 3 has an important exception. Two players in the final are called
Martínez (Lautaro and Emiliano, the goalkeeper), and two are called Hernández
(Theo and Ángel Di María Hernández). In those cases the surname alone is
**ambiguous** and **does not count**: answering only "Martínez" is wrong.
Compound surnames work: "Di María", "De Paul", "Mac Allister", "Kolo Muani".

---

## 5.4 The four outcomes of an answer

Every run ends in exactly one of these:

| Outcome | When it happens | Counts as |
|---|---|---|
| **Correct** | the answer matches the ground truth | right |
| **Hallucination** | answered, with an air of certainty, and was wrong | error |
| **Abstention** | said `no_data` on a question that **has** an answer | error, but recorded separately |
| **Format error** | did not produce a valid `Answer`, even after the 2 retries, hit the call limit, or spent the output token cap (`LLM_MAX_TOKENS`) reasoning before answering | error, recorded separately |

Why split the errors? Because they have **different costs** for whoever uses
the system:

- an **abstention** is an honest error: the user knows there is no answer;
- a **hallucination** is dangerous: the user gets a wrong answer delivered with
  confidence and has no way of knowing;
- a **format error** is an engineering problem (the model or the provider did
  not handle the format well), not a knowledge one. With reasoning models, it
  includes the case where the reasoning uses up the whole output cap and no
  answer comes out: with Sonnet 4.6, this happened in `events_in_prompt`, which
  requires counting through the whole table (chapter 7).

An arm with 70% correct and 30% abstention is much more reliable than one with
70% correct and 30% hallucination.

On `unanswerable` questions, any answer other than `no_data` is a
hallucination.

---

## 5.5 What gets recorded: `results.jsonl`

Each run (one question × one arm × one repeat) becomes **one line** in
`data/benchmark/results.jsonl`, written right after the call. The format is
JSON Lines: one JSON object per line. The fields:

| Field | Example | Meaning |
|---|---|---|
| `question_id`, `type`, `arm`, `repeat` | `"a05"`, `"filtered_aggregation"`, `"graph_tools"`, `1` | what was run |
| `answer` | `{"rationale": "...", "players": [...], "value": 26, "no_data": false}` | the full answer (`null` if there was a format error) |
| `expected` | `{"players": ["Enzo Fernandez"], "accepted": [["Enzo Fernandez"]], "value": 26, "no_data": false}` | the ground truth, with the equally right answers in `accepted` |
| `correct`, `abstention`, `format_error` | `true`, `false`, `false` | the outcome (5.4) |
| `error` | `null` | the reason, when there was no valid answer |
| `input_tokens`, `output_tokens` | `2817`, `95` | tokens used, as reported by the provider |
| `n_tool_calls`, `tool_calls` | `2`, `[{"tool": "list_actions", "args": {...}}, ...]` | tools called (only in the tool arms) |
| `latency_s` | `3.2` | run time, in seconds |
| `cache_read_tokens`, `cache_write_tokens` | `100945`, `0` | tokens read from and written to the prompt cache (chapter 7) |
| `trace_url` | `"https://us.cloud.langfuse.com/project/.../traces/..."` | link to the Langfuse trace (`null` without Langfuse) |
| `model`, `timestamp` | `"openrouter:..."` or `"bedrock:..."`, `"2026-10-07T14:43:00+00:00"` | provider and model used, and when |

This file is the **single source of the numbers**. Everything in the report
comes from it.

---

## 5.6 How to read the report: `summary.md`

At the end of the run, `scripts/run_benchmark.py` generates
`data/benchmark/summary.md`. To regenerate it without calling any model:
`python scripts/summarize.py`. The sections:

### 1. Accuracy by type and arm (the main table)

Rows are the question types, columns are the arms, and each cell is the % of
correct runs (every repeat counts). The last rows are the total and the total
**without the `unanswerable` ones**: an arm that answers "no data" to
everything gets every `unanswerable` right, and that row removes the effect.

How to read it: compare **columns** to see which arm does better on each type.
Compare **rows** to see which kind of question is hard for everyone. Types
are small (1 to 10 questions each), so **one question is worth 10 to 100
percentage points** inside its type, with any number of repeats. Differences of one or
two questions between arms should not be read as superiority.

### 2. Errors by arm

For each arm, the % of hallucination, abstention and format error, over all
the runs of that arm. This is where you see whether an arm fails "honestly"
(abstains) or "confidently" (hallucinates).

### 3. Consistency across repeats

The % of questions in which all the repeats gave **exactly the same answer**
(same players, same number, same `no_data`). Even at temperature 0, models
served by providers are not always deterministic. An inconsistent arm is less
reliable, even if it is right on average.

### 4. Cost per question

Input and output tokens, number of tool calls and time, all as averages per
run. The money cost is tokens × your model's price. `events_in_prompt` should
show tens of thousands of input tokens; the tool arms, several calls.

### 5. Hits per question

For each question and arm, how many of the repeats were right (for example,
`2/3`). This is the table for investigation: find the `0/3` cell and go to
`results.jsonl` (or to Langfuse) to see the `rationale` and the tools called.

---

## 5.7 Langfuse: for investigating, not for measuring

If the Langfuse keys are in `.env`, each run shows up in Langfuse as a block
named `{question}/{arm}/r{n}` (for example, `s01/graph_tools/r1`). Inside it
is the whole conversation: the prompt sent, each tool call with its result and
the final answer. This is very useful for understanding an error.

Each line of `results.jsonl` keeps the link to its own trace (`trace_url`),
and `ask.py` prints it. The [run log](runs/README.md) uses these links in a
table by question and arm. The Langfuse project is private, so the links only
open for project members.

But **the benchmark numbers come from `results.jsonl`, never from Langfuse.**
Langfuse is an external service and can lose or delay records. The local file
is written run by run and is versioned in the repository. Without the keys,
everything works the same, just without this view.
