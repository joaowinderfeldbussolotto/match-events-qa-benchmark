# 9. Every data transformation

This chapter lists, in order, everything that happens to the data from the raw
StatsBomb JSON to the text each arm gives the model. Each item says **what**
the transformation does, **where** it is in the code and, when it is not
obvious, **why**. Chapters 2 and 4 tell the same story with examples; this one
is the full reference.

Column names and values from the code are kept as they are (many are in
Portuguese; chapter 2 and the [glossary](08-glossary.md) explain them).

The path has four stretches:

```text
raw JSON ──► layer 0 (action table) ──► layers 1 and 1b (Neo4j) ──► what each arm sees
                  │                                                       ▲
                  └──────────────────── event table ──────────────────────┘
```

The ground truth takes its own path from the raw JSON and layer 0
(section 9.6).

---

## 9.1 The source: the raw JSON

| File | Content |
|---|---|
| `data/raw/statsbomb/events/3869685.json` | ~4,400 events of the final, each with type, time, team, player and location |
| `data/raw/statsbomb/lineups/3869685.json` | lineups, with each player's name and nickname |

In the StatsBomb events, the location of each event is given **from the point
of view of whoever acts**: the team performing the action always attacks
towards increasing x, on a 120 × 80 pitch.

The **penalty shootout (period 5) is dropped** throughout the project: it is
not open play and does not enter any count.

---

## 9.2 Layer 0: from events to an action table

Code: `src/football_graphrag/ingestion/` (orchestrated by `pipeline.py`).
Output: `data/processed/3869685.parquet` (one row per action) and auxiliary
files (`_phases`, `_windows`, `_pressures`, `_meta`).

### 1. Reading (`statsbomb_loader.py`)

The `kloppy` library reads the events and lineups into a model shared by
several data vendors. Every event type is read; period 5 is dropped here.

### 2. Conversion to SPADL (`spadl_transform.py`)

The `socceraction` library converts the events into **SPADL actions**:

- only on-ball actions are kept, in a closed vocabulary of ~23 types;
  auxiliary events (ball receipt, half start, pressure, block...) are dropped;
- each action gets the same fields: time in the period, team, player, start
  and end coordinates, type, result (success or failure) and body part;
- the coordinates are converted to meters, on a 105 × 68 pitch;
- the library itself adjusts clearances and inserts **carries** between two
  actions of the same player when the ball moved with them.

The ~4,400 events become 2,585 actions.

### 3. Every action attacking left to right (`spadl_transform.py::_play_left_to_right`)

The conversion from `kloppy` gives the home team (Argentina) attacking to the
right in odd periods, and the sides swap every period. Layer 0 mirrors
(x → 105 − x, y → 68 − y, at start and end) the home team's actions in even
periods and the away team's in odd ones. After that, in every action, high x
means "near the opponent's goal" and "left" is the attacker's left.

Two tests guarantee this: each action is in the same place as in the raw JSON
(up to the rounding of the scale), and every shot is in the attacking third.

### 4. Names

The player and team names come from `socceraction`'s local loader, by id.

### 5. xT, expected threat (`spadl_transform.py::add_xt`)

The pitch is divided into a 12 × 8 grid of cells, and each cell has a value:
the chance that a possession going through it ends in a goal. An action's xT
is `value(end cell) − value(start cell)`. It is only computed for **completed
passes, crosses and carries**; other actions get 0.

The grid is fitted once on the 16 knockout games of the 2022 World Cup, with
those games' actions also turned left to right, and stored in
`data/models/xt_fitted_12x8.json`.

### 6. VAEP (`spadl_transform.py::add_vaep`)

Another value per action: how much it changed the team's chance of scoring
(offensive component) and of conceding (defensive) in the following actions.
It comes from a machine learning model trained once on the same 16 games. That
model expects the original SPADL layout (home team to the right, away team to
the left) and flips the actions on its own. So the away team's actions are
mirrored back just for this computation.

### 7. Zones (`tactical_metrics.py::add_zones`)

Each action gets `zone_start` and `zone_end`, the start and end cell in the
grid of 12 columns × 8 rows: `zone = column × 8 + row`. Column 0 is next to the
team's own goal and 11 next to the opponent's goal.

### 8. Possession phases (`tactical_metrics.py::add_possession_phases`)

`possession_id` numbers runs of consecutive actions by the same team. A new
phase starts when the team changes, when the period changes, or after an
action that ends the play: foul, shot, goalkeeper save, clearance or bad
touch. The final has 537 phases.

### 9. Progressive pass (`tactical_metrics.py::add_progressive_flag`)

A completed pass or carry is **progressive** if it brought the ball closer to
the center of the opponent's goal by at least 30 m (starting and ending in the
team's own half), 15 m (crossing the halfway line) or 10 m (entirely in the
opponent's half). Wyscout's definition.

### 10. Pass receiver (`tactical_metrics.py::add_pass_receivers`)

The receiver of a completed pass is the player **of the same team** who
performs the next action. If the next action is the opponent's, the pass has
no receiver.

### 11. Team metrics and auxiliary tables (`tactical_metrics.py`, `pressure_events.py`)

| Metric | How it is computed |
|---|---|
| Summary per possession phase | per phase: team, period, start and end, start and end zone, summed xT, number of actions |
| Rolling windows | PPDA and field tilt in 10-minute windows, every 5 minutes |
| Pressures | read straight from the raw JSON ("Pressure" events): who pressed whom, where and when |
| PPDA | the opponent's passes in the first 60% of their pitch (x ≤ 63 m) ÷ the team's defensive actions in that same space (x ≥ 42 m, from its point of view). The lower, the more pressure. Computed for the 1st and 2nd halves |
| Field tilt | the team's passes in the final third (x ≥ 70 m) ÷ both teams' passes in their respective final thirds |

### 12. Football vocabulary (`football_semantics.py::add_football_semantics`)

| Column | Rule |
|---|---|
| `acao` (action) | the SPADL type translated: `pass` → `passe`, `dribble` → `conducao`, `take_on` → `drible`, `tackle` → `desarme`, `keeper_save` → `defesa_do_goleiro`, etc. (23 values) |
| `grupo_acao` (action group) | grouping: `passe` (pass, cross, throw-in, goal kick), `bola_parada` (corners and free kicks taken), `finalizacao` (shot), `conducao`, `drible`, `defensiva`, `infracao`, `erro`, `goleiro` |
| `sucesso` (success) | the SPADL "success" result |
| `minuto` (minute) | broadcast minute: period start (0, 45, 90, 105) + full minutes in the period + 1. Stoppage time continues the count (the 1st half goes to 53') |
| `segundo` (second) | game clock in seconds: period start (0, 2700, 5400, 6300) + seconds in the period |
| `periodo_nome` (period name) | "1º tempo", "2º tempo", "1ª prorrogação", "2ª prorrogação" (1st half, 2nd half, 1st and 2nd half of extra time) |
| `gol` (goal) | a successful shot (shot, penalty, direct free kick) |
| `cartao_amarelo` (yellow card) | the SPADL "yellow_card" result |
| `corpo` (body) | the body part, in Portuguese |
| `terco` (third) | by the start zone: columns 0–3 `defesa`, 4–7 `meio`, 8–11 `ataque` |
| `corredor` (corridor) | by the start zone, facing the opponent's goal: rows 0–2 `direita` (right), 3–4 `centro`, 5–7 `esquerda` (left) |

### 13. What SPADL loses, recovered from the raw JSON (`football_semantics.py::enrich_from_statsbomb`)

The join is by the original event id, which the conversion keeps.

- **Shot outcome** (`desfecho`, `no_gol`): `gol` (goal), `defendida` (saved),
  `para_fora` (off target), `na_trave` (post) or `bloqueada` (blocked). On
  target = goal or saved.
- **Card for dissent**: SPADL only sees a card that came with a foul. Giroud's
  yellow card for dissent becomes a row of its own, with the action
  `cartao_por_reclamacao`.

### Known differences between the JSON and layer 0

- Some passes in the JSON do not become SPADL actions. Completed passes match;
  attempted ones are 1 or 2 short for some players.
- A goalkeeper coming out to clear the ball is classified as a save: Lloris
  has 8 saves in layer 0 and 7 in the JSON.

---

## 9.3 Layers 1 and 1b: the graph in Neo4j

Code: `src/football_graphrag/graph/build.py` and `statistics.py`. Nothing is
computed again: each layer 0 row becomes a node or an edge.

| In the graph | Comes from |
|---|---|
| `Jogador` (player), `Time` (team), `Partida` (match), `Zona` (96), `FaseDePosse` (537 possession phases) | layer 0 and lineups |
| `REALIZOU` ("performed", player → match) | one per action, with layer 0's football columns (action, success, minute, second, period, goal, card, outcome, third, corridor, zone, xT, VAEP, phase) |
| `PASSOU_PARA` ("passed to", player → player) | one per **completed pass with a receiver**, of the pass types (pass, cross, throw-in, goal kick, corners and free kicks taken); keeps xT, zones and phase |
| `DEU_ASSISTENCIA` ("assisted") | for each goal, the last pass to the scorer in the same possession phase |
| `FINALIZOU`, `PRESSIONOU`, `ATUOU_EM`, `PARTICIPOU_DE`, `PROGREDIU_PARA` | shots, pressures, actions per zone, players per phase, progressions between zones |
| `EstatisticaJogador`, `EstatisticaTime` (layer 1b) | the stat sheet, counted by Neo4j itself over the edges above (touches, passes, tackles, fouls, shots, xT, PPDA, field tilt...) |

Layer 2 (`PadraoTatico`, tactical pattern) exists in the database, but **no arm
reads it**.

---

## 9.4 What each arm receives

### `no_context`

Nothing besides the question.

### The event table (`events_in_prompt` and `vector`)

Code: `benchmark/arms.py::event_lines`. One CSV row per layer 0 action, 2,585
rows:

1. **Order:** period, time in the period, action number. The card recovered
   from the JSON goes in its right place in the game, not at the end.
2. **Columns:** `period, minute, team, player, action, success, receiver,
   zone_from, zone_to, possession, outcome, score`.
3. **`receiver`:** the name of the pass receiver (step 10), empty for other
   actions.
4. **`outcome`:** joins, separated by `+`:
   - `goal(A-F)`, with the score **after** the goal (Argentina-France);
   - `yellow_card`;
   - the shot outcome, when it is not a goal (`defendida`, `bloqueada`,
     `para_fora`).
5. **`score`:** the score **before** the action, Argentina-France. On a goal's
   row, `score` shows the score before it and `outcome` the score it made:
   ```text
   1,36,Argentina,Ángel Fabián Di María Hernández,finalizacao,1,,92,91,132,goal(2-0),1-0
   ```
6. The table is preceded by a legend in English that explains each column.

`events_in_prompt` receives the whole table (~110 thousand tokens). `vector`
receives **30 rows**:
- each row is turned once into a vector (embedding), which is cached;
- the question also becomes a vector;
- the 30 rows with the highest cosine similarity to the question go to the
  model, put back in game order and with the same legend.

### The stat sheet (`stats_in_prompt`)

Code: `benchmark/arms.py::stats_table`. Read from Neo4j (layer 1b): one row per
team and one per player, with every field except the internal identification
ones. The tables are preceded by a glossary of each field
(`tools.STAT_GLOSSARY`).

### The `graph_tools` tools

Code: `benchmark/tools.py` (queries) and `benchmark/arms.py` (the descriptions
the model reads). The model receives no data: it calls tools, which query
Neo4j and return data.

**Common filters** (`query_actions`, `list_actions`, `pass_network`,
`pass_paths`), applied over `REALIZOU`:

| Filter | Rule |
|---|---|
| `team`, `player` | team and player of whoever acted. Full name, nickname or unique surname; an ambiguous name returns the candidates |
| `action` | one or more values from layer 0's vocabulary |
| `success` | completed or failed action |
| `period` | one or more periods (1 to 4) |
| `second_from`, `second_to` | a window of **continuous time**, in seconds since kick-off, with no breaks. Each period starts where the last action of the previous one ended. Compared to 3 decimal places, the same precision `list_actions` shows |
| `third`, `corridor` | third and corridor where the action starts (step 12), in English |
| `goal`, `yellow_card` | flags on the action |
| `assist` | the pass that was the assist: the last pass received by the scorer in the same possession phase |

**The eight tools:**

| Tool | What it computes |
|---|---|
| `list_players` | players with at least one action, with team and position |
| `query_actions` | counts the filtered actions (or adds up their xT), grouped by player, receiver, team, action, period, third or corridor; from largest to smallest |
| `list_actions` | the filtered actions, in order: period, minute, continuous second, team, player, action, success, receiver, third, corridor, `score` (score before the action, "Argentina 2-1 France") and `outcome` (on a goal, with the score after: "goal (score after: Argentina 2-2 France)"). Up to 100 rows, plus the total found |
| `query_possessions` | a team's possession phases (plays) that pass the filters: period, time window by the possession's start, third where it starts, third it reaches, action it ends with, players who all took part; counts the plays, or ranks them by player or by pair of teammates by the number of plays they took part in |
| `pass_network` | a team's passing network: the completed passes between teammates that pass the filters, summed per passer → receiver pair (number of passes and xT). Returns an identifier, the team and the filters used |
| `network_metric` | a metric over the network, computed by Neo4j GDS |
| `network_edges` | the network's links (passer, receiver, passes, xT), from strongest to weakest; with a player, only theirs |
| `pass_paths` | pass sequences in which each pass comes from whoever received the previous one. The link is the next pass the receiver attempts, and the sequence stops if that pass fails. Counts the most repeated player sequences |

**`network_metric` details:**

- **On-demand projection:** at each call, the network is projected into GDS,
  computed and dropped.
- **Direction:**
  - `directed`: keeps passer → receiver;
  - `undirected`: adds up both directions of each pair into a single link.
- **Weight in betweenness:** becomes a path length:
  - `none`: every link has length 1;
  - `passes`: 1/passes;
  - `xt`: 1/(1+xT).
- **Weight in degree, PageRank and communities:** becomes a strength: the
  number of passes, or the xT with negative totals counted as zero.
- **Bridges and articulation points:** always unweighted and undirected.
- **Communities:** the Louvain algorithm, undirected; the groups may vary
  between calls.
- **Degree in the directed network:** returns out- and in-degree separately.

**`pass_paths` details:**

- `players` is the number of players in the sequence, from 3 to 5 (3 = A → B →
  C).
- `same_possession` requires the whole sequence to be in the same possession
  phase.
- `consecutive` requires that there be no other pass, by anyone, between two
  linked passes.
- The filters only select the first pass of the sequence.
- A player can repeat (A → B → A).

**Execution:**

- The model calls one tool at a time, up to 12 per question; from the 13th on,
  it gets "limit reached".
- An invalid argument comes back as an error message, for the model to fix.

### `text_to_cypher` (optional)

- The schema the model reads is generated from Neo4j on each process
  (`benchmark/cypher.py`): labels, edges, counts in the match, properties with
  type, range and, for text properties with up to 25 values, the full list.
  `PadraoTatico`, `OBSERVADO_EM` and the internal properties (`uid`,
  `tipo_spadl`, `pressure_idx`) are left out.
- The model's query goes through a filter (read-only, no procedures, no
  `PadraoTatico`) and runs in a read session, with 15 s and up to 50 rows.
  Nodes and edges in the result become their properties; numbers with decimal
  places are rounded to 4 places.

### What applies to every arm

- **The same model,** at temperature 0 (with the exceptions of chapter 4,
  section 4.1).
- **The same answer format:** reasoning, players, number and "no data". The
  format refuses an empty answer.
- **The same system instruction.** It says the questions are about one match,
  without saying which. It says to answer only with the data provided and to
  mark "no data" when the data does not have **exactly** what the question
  asks, without replacing it with another, approximate measure.

---

## 9.5 Player names

The data uses StatsBomb's full name ("Lionel Andrés Messi Cuccittini"). To
check answers and resolve names in the tools, `scoring.py` builds aliases from
the lineups:

- the full name and the nickname count;
- the surname counts too, but **only when it is unique** in the match.
  "Martínez" is ambiguous (Lautaro and Emiliano) and does not resolve on its
  own.

The comparison ignores accents and case.

---

## 9.6 The ground truth: a separate path

Code: `benchmark/ground_truth.py`. The ground truth **never reads Neo4j**:

- facts and simple counts come from the raw JSON;
- counts that depend on layer 0 definitions (tackle won, pass with a receiver)
  come from the Parquet;
- networks and sequences are computed with `networkx` and pandas, over the
  Parquet.

Each question is answered under **every reasonable reading**, combining:

| Axis | Readings |
|---|---|
| Set of passes | every completed pass · only open-play passes (`passe`) |
| Link weight | none · number of passes · xT |
| Direction | passer → receiver · both directions added up |
| Time slice | with the event that defines the cut · without it |
| Third | where the pass starts · where it ends |
| Sequences | same possession or not · consecutive passes or not |
| Source | raw JSON · layer 0 |

A question only stays in the benchmark if some answer is right under every
reading, in what the check looks at. In a tie within a reading, all those tied
at the top count for that reading; the accepted answers (the ground truth's
`accepted` field) are those at the top under every reading. The readings of
each question are in `data/benchmark/robustness.md`.

The cross-check (`scripts/check_ground_truth.py`) answers each question again
through the `graph_tools` tools, with a fixed sequence of calls, and compares
with the ground truth.
