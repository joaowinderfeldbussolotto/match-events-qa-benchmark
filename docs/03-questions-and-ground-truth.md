# 3. Questions and ground truth

A benchmark is only worth what its right answers are worth. This chapter
explains how the questions were written, where they live, how the right answer
to each one is computed, how it is tested not to depend on how the question is
read, and how the computation is checked.

---

## 3.1 Where the questions live: `config/questions.yaml`

The questions live in a configuration file, separate from the code:
[`config/questions.yaml`](../config/questions.yaml). An entry looks like this:

```yaml
  - id: s01
    type: network_slice
    stage: pilot
    check: player
    text: >-
      Na prorrogação, quem foi o principal elo da circulação de bola da França?
```

(In English: "In extra time, who was the main link in France's ball
circulation?" The questions are written and sent to the models in Portuguese;
the benchmark was designed in Portuguese, and translating them would change the
experiment.)

What each field means:

| Field | What it is for |
|---|---|
| `id` | a short identifier. The letter gives the type: **f** (fact), **a** (filtered_aggregation), **n** (network), **s** (network_slice), **t** (structure), **c** (counterfactual), **q** (sequence), **p** (play), **b** (substitution), **u** (unanswerable) |
| `type` | the question type (table below) |
| `stage` | whether the question is part of the run (`pilot`, `full`, `graph`), kept in reserve (`candidate`) or dropped by the robustness test (`removed`) |
| `check` | **how** the answer is scored (table below) |
| `tolerance` | optional. Margin accepted for continuous numbers. Counts are exact and do not use it |
| `text` | the question, **exactly** as it goes to the model |
| `note` | a comment for whoever reads the file; for a removed question, the reason. **It never goes to the model** |

At the top of the file, `active_stages` says which stages are part of the run.
Today they are `[pilot, full, graph]`: **52 active questions**. The file has 81
questions written: the 52 active ones, 22 removed by the robustness test and 7
in reserve (`candidate`). The first 25 (`pilot` and `full`, 5 of each of the
first five types) were those of the early rounds; the 27 `graph` questions came
later, with the types that look at plays, substitutions and the structure of the
network.

The types:

| `type` | What the question requires |
|---|---|
| `fact` | finding an event: who committed the penalty foul, who gave the pass for the goal |
| `filtered_aggregation` | filtering, counting and ranking within a slice: "in extra time", "after 2–2", "while leading 2–0" |
| `network` | a passing network concept over the whole match: pair, link, sequence of three |
| `network_slice` | a network concept within a slice, or comparing slices |
| `structure` | the structure of the passing network: who, if removed, would leave teammates isolated |
| `counterfactual` | "if so-and-so were not on the pitch": the network recomputed without one player |
| `sequence` | what happens right before an action: the second-to-last pass, the pass before the shot |
| `play` | whole plays (possessions): where they start, where they get to, how they end, who takes part |
| `substitution` | before and after a substitution: how the ball circulation changed |
| `unanswerable` | looks answerable from events, but the data does not have what is asked |

For the results, the types are gathered into **five groups**, easier to explain:

| Group | Types | Questions |
|---|---|---|
| Search and counting | `fact`, `filtered_aggregation` | 11 |
| Pass network relations | `network`, `network_slice`, `structure`, `counterfactual` | 20 |
| Plays and sequences | `sequence`, `play` | 10 |
| Before and after a game moment | `substitution` | 6 |
| Control: no answer | `unanswerable` | 5 |

The groups live in `benchmark/questions.py` (`GROUPS`).

The scoring types (`check`):

| `check` | The answer is right when... | Example |
|---|---|---|
| `player` | the **first** player of the answer is the expected one | "Who committed the most fouls in the second half?" |
| `value` | the number is the expected one | "How many shots did Argentina take after 2–2?" |
| `set` | the **set** of players is the expected one, in any order | "Which France pair exchanged the most passes?" |
| `player_and_value` | player **and** number are both right | "Which player completed the most passes during the 2–0, and how many?" |
| `no_data` | the model said the data cannot answer | "How many minutes did Messi spend in the attacking half?" |

The file is **validated on load** (`benchmark/questions.py`). The program refuses
to run if:
- an id is repeated;
- a type, `check` or `stage` is unknown;
- the letter of the `id` does not match the type;
- a removed question does not give its reason;
- when `per_type` is set, a type does not add up to that number of active
  questions.

---

## 3.2 The rules for writing a question

Each rule exists to avoid one specific way the benchmark could measure the
wrong thing.

**1. Closed, with a single answer.** "Who", "how many", "which", never
"explain". An open question would need someone, or another LLM, to judge the
answer. With a closed question, scoring is an `if`.

**2. Football language, no operational definition.** The question speaks like
a commentator: "the main link in the ball circulation", "the pair that
exchanged the most passes", "the sequence of three players that repeated the
most". It does not say how to compute it ("A passes to B in the same
possession, with no other pass in between"). The test `tests/test_questions.py`
fails if any question uses the name of a tool or an algorithm ("betweenness",
"pagerank", "rede" (network), "grafo" (graph), "xT", "pass_paths" and so on).

**3. Never copy a tool description.** The `graph_tools` tools have English
descriptions with the football reading of each metric (chapter 4). A question
that translated that text word for word would point the model to the tool.
This check is manual.

**4. Tools before questions.** The tools are written and frozen before the
questions that test them are written. No tool is created for a question. A test
(`tests/test_tools_frozen.py`) stores a hash of the definitions.

**5. Stable under every reading.** With no definition in the text, the same
question can be read in more than one way. The answer is computed under every
reasonable reading (3.5). If it changes, the question goes; it is not fixed by
adding a definition to the text.

**6. Nothing that depends on where the sources disagree.** "Attempted passes"
and "goalkeeper saves" have different numbers in the raw JSON and in layer 0
(chapter 9), so they are not asked.

**7. No data means no data in any source.** The `unanswerable` questions ask
for something not even StatsBomb's 360 data has: time in each part of the
pitch, distance covered, speed, passive offside.

**8. A tie does not disqualify.** If, under one reading, two players tie, the
right answer accepts either of them, or both together. A question only goes if
the answer **changes** from one reading to another; a tie within one reading
does not change the answer, it only gives it more than one right form (the
`accepted` field of the ground truth, chapter 5).

---

## 3.3 The 52 questions and their right answers

Names are shortened here; the ground truth uses the full registered name. "or"
separates equally right answers (a tie within one reading).

### Search and counting (11)

| id | Question (as sent, in Portuguese) | In English | Right answer |
|---|---|---|---|
| f01 | Quem recebeu o primeiro cartão amarelo da final? | Who received the first yellow card of the final? | Enzo Fernández |
| f02 | Quem cometeu a falta que deu origem ao primeiro pênalti da final? | Who committed the foul that led to the first penalty of the final? | Dembélé |
| f03 | No lance do gol de Messi na prorrogação, o goleiro francês tinha feito uma defesa instantes antes. Quem deu o chute que ele defendeu? | In the play of Messi's extra-time goal, the French goalkeeper had made a save moments before. Who took the shot he saved? | Lautaro Martínez |
| f04 | Quem deu o passe para o gol que deixou o placar em 2 a 2 no tempo normal? | Who gave the pass for the goal that made it 2–2 in normal time? | Marcus Thuram |
| f05 | Quem fez a última finalização da França na final, antes da disputa de pênaltis? | Who took France's last shot of the final, before the penalty shootout? | Kolo Muani |
| a01 | Quem deu mais passes certos no terço final do campo pela Argentina? | Who completed the most passes in the final third for Argentina? | Messi |
| a02 | Quem deu mais passes certos no terço final do campo pela França? | Who completed the most passes in the final third for France? | Rabiot |
| a03 | Depois do gol que deixou o placar em 2 a 2 no tempo normal, quantas finalizações a Argentina fez até o fim da prorrogação? | After the goal that made it 2–2 in normal time, how many shots did Argentina take until the end of extra time? | 10 |
| a05 | Enquanto a Argentina vencia por 2 a 0, qual jogador argentino acertou mais passes, e quantos? | While Argentina was leading 2–0, which Argentina player completed the most passes, and how many? | Enzo Fernández, 26 |
| a06 | Na prorrogação, quem fez mais desarmes certos pela Argentina? | In extra time, who made the most successful tackles for Argentina? | Enzo Fernández |
| a07 | No segundo tempo, quem cometeu mais faltas? | In the second half, who committed the most fouls? | Julián Álvarez |

### Pass network relations (20)

| id | Question (as sent, in Portuguese) | In English | Right answer |
|---|---|---|---|
| n03 | Na troca de passes da Argentina, qual jogador, se não estivesse em campo, deixaria algum companheiro sem trocar passes com ninguém do time? | In Argentina's passing, which player, if he were not on the pitch, would leave some teammate without exchanging passes with anyone on the team? | Otamendi |
| n04 | Qual dupla da França mais trocou passes entre si na final? | Which France pair exchanged the most passes with each other in the final? | Upamecano and Varane |
| n05 | Qual dupla da Argentina mais trocou passes entre si na final? | Which Argentina pair exchanged the most passes with each other in the final? | Romero and Otamendi |
| n06 | Qual jogador da Argentina trocou passes com o maior número de companheiros diferentes na final? | Which Argentina player exchanged passes with the largest number of different teammates in the final? | Enzo Fernández |
| n09 | Qual sequência de três jogadores da França, com a bola passando de um para o outro, mais se repetiu na final? | Which sequence of three France players, with the ball going from one to the next, repeated the most in the final? | Upamecano, Koundé and Varane |
| n11 | Para cortar a bola que chega a Messi, preciso saber: qual companheiro mais passou a bola para ele na final? | To cut off the ball that reaches Messi, I need to know: which teammate passed the ball to him the most in the final? | De Paul |
| n12 | Para marcar Mbappé, preciso saber: qual companheiro mais passou a bola para ele na final? | To mark Mbappé, I need to know: which teammate passed the ball to him the most in the final? | Theo Hernández |
| s01 | Na prorrogação, quem foi o principal elo da circulação de bola da França? | In extra time, who was the main link in France's ball circulation? | Koundé |
| s03 | Depois do gol que deixou o placar em 2 a 2 no tempo normal, qual dupla da França mais trocou passes entre si? | After the goal that made it 2–2 in normal time, which France pair exchanged the most passes with each other? | Koundé and Varane |
| s04 | A dupla da Argentina que mais trocou passes entre si no primeiro tempo continuou sendo a principal no segundo tempo? Qual foi a dupla que mais trocou passes no segundo tempo? | Was the Argentina pair that exchanged the most passes in the first half still the main one in the second half? Which pair exchanged the most passes in the second half? | Enzo Fernández and De Paul |
| s06 | No segundo tempo, qual companheiro mais recebeu passes de Enzo Fernández? | In the second half, which teammate received the most passes from Enzo Fernández? | De Paul |
| s07 | Na prorrogação, qual sequência de três jogadores da Argentina, com a bola passando de um para o outro, mais se repetiu? | In extra time, which sequence of three Argentina players, with the ball going from one to the next, repeated the most? | Romero, Enzo Fernández and Otamendi |
| s09 | Na prorrogação, qual jogador da Argentina trocou passes com o maior número de companheiros diferentes? | In extra time, which Argentina player exchanged passes with the largest number of different teammates? | Enzo Fernández |
| s10 | No campo de ataque, pelo lado direito, quais dois jogadores da Argentina mais trocaram passes entre si? | In the attacking half, on the right side, which two Argentina players exchanged the most passes with each other? | Messi and De Paul |
| s11 | No campo de ataque, pelo lado esquerdo, quem foi o jogador da Argentina mais procurado pelos companheiros? | In the attacking half, on the left side, who was the Argentina player most sought by his teammates? | Mac Allister |
| s12 | Enquanto a França perdia por 2 a 0, quem foi o jogador francês mais procurado pelos companheiros? | While France was losing 2–0, who was the France player most sought by his teammates? | Upamecano |
| s13 | Depois do gol que deixou o placar em 2 a 2 no tempo normal, quem passou a ser o jogador da França mais procurado pelos companheiros? | After the goal that made it 2–2 in normal time, who became the France player most sought by his teammates? | Koundé |
| t06 | Na prorrogação, qual jogador da França, se não estivesse em campo, deixaria algum companheiro sem trocar passes com ninguém do time? | In extra time, which France player, if he were not on the pitch, would leave some teammate without exchanging passes with anyone on the team? | Koundé |
| c01 | Se Enzo Fernández não estivesse em campo, quem passaria a ser o principal elo da circulação de bola da Argentina? | If Enzo Fernández were not on the pitch, who would become the main link in Argentina's ball circulation? | Otamendi |
| c02 | Sem Otamendi em campo, algum companheiro da Argentina ficaria sem trocar passes com ninguém do time? Quem? | Without Otamendi on the pitch, would any Argentina teammate be left without exchanging passes with anyone on the team? Who? | Pezzella |

### Plays and sequences (10)

| id | Question (as sent, in Portuguese) | In English | Right answer |
|---|---|---|---|
| q01 | Qual jogador argentino mais vezes finalizou logo depois de receber um passe de um companheiro? | Which Argentina player most often shot right after receiving a pass from a teammate? | Lautaro Martínez |
| q03 | Quem deu mais vezes o penúltimo passe nas jogadas da Argentina que terminaram em finalização? | Who most often gave the second-to-last pass in Argentina's plays that ended in a shot? | Julián Álvarez |
| p01 | Quais dois jogadores argentinos mais vezes participaram juntos das mesmas jogadas que chegaram ao terço final? | Which two Argentina players most often took part together in the same plays that reached the final third? | Enzo Fernández and Messi |
| p02 | Qual jogador participou de mais jogadas da Argentina que começaram no próprio campo de defesa e terminaram em finalização? | Which player took part in the most Argentina plays that started in their own defensive half and ended in a shot? | Messi |
| p03 | Qual jogador participou de mais jogadas da Argentina que terminaram em finalização? | Which player took part in the most Argentina plays that ended in a shot? | Messi |
| p04 | Qual jogador participou de mais jogadas da França que terminaram em finalização? | Which player took part in the most France plays that ended in a shot? | Mbappé |
| p05 | Nas jogadas da Argentina que terminaram em finalização e em que Messi tocou na bola, qual companheiro mais participou junto com ele? | In Argentina's plays that ended in a shot and in which Messi touched the ball, which teammate took part with him the most? | Enzo Fernández |
| p06 | Nas jogadas da França que terminaram em finalização e em que Mbappé tocou na bola, qual companheiro mais participou junto com ele? | In France's plays that ended in a shot and in which Mbappé touched the ball, which teammate took part with him the most? | Rabiot |
| p07 | Quais dois jogadores franceses mais vezes participaram juntos das mesmas jogadas que chegaram ao terço final? | Which two France players most often took part together in the same plays that reached the final third? | Rabiot and Tchouaméni or Rabiot and Mbappé |
| p08 | Quem participou de mais jogadas da França que levaram a bola da defesa até o terço final no segundo tempo? | Who took part in the most France plays that took the ball from defense to the final third in the second half? | Kolo Muani |

### Before and after a game moment (6)

| id | Question (as sent, in Portuguese) | In English | Right answer |
|---|---|---|---|
| b02 | Depois que Di María foi substituído, qual companheiro mais passou a bola para Messi? | After Di María was substituted, which teammate passed the ball to Messi the most? | Enzo Fernández |
| b03 | Depois que Dembélé foi substituído no primeiro tempo, qual companheiro mais passou a bola para Mbappé? | After Dembélé was substituted in the first half, which teammate passed the ball to Mbappé the most? | Rabiot |
| b05 | Depois que Dembélé foi substituído no primeiro tempo, para qual companheiro Mbappé mais passou a bola? | After Dembélé was substituted in the first half, which teammate did Mbappé pass the ball to the most? | Kolo Muani |
| b06 | Depois que Dembélé foi substituído no primeiro tempo, qual dupla francesa mais trocou passes entre si? | After Dembélé was substituted in the first half, which France pair exchanged the most passes with each other? | Koundé and Varane |
| b07 | Depois que Di María foi substituído, qual companheiro mais recebeu passes de Messi? | After Di María was substituted, which teammate received the most passes from Messi? | Enzo Fernández |
| b09 | Depois que Di María foi substituído, quem passou a ser o jogador da Argentina mais procurado pelos companheiros? | After Di María was substituted, who became the Argentina player most sought by his teammates? | Enzo Fernández |

### Control: no answer (5)

| id | Question (as sent, in Portuguese) | In English | Right answer |
|---|---|---|---|
| u01 | Quantos minutos Messi passou no campo de ataque durante a final? | How many minutes did Messi spend in the attacking half during the final? | no data |
| u02 | Qual foi a distância total percorrida por Rodrigo De Paul na final? | What was the total distance covered by Rodrigo De Paul in the final? | no data |
| u03 | Quantos piques em alta velocidade Mbappé deu na prorrogação? | How many high-speed sprints did Mbappé make in extra time? | no data |
| u04 | A que velocidade saiu o chute de Mbappé no gol que deixou o placar em 2 a 2? | How fast was Mbappé's shot on the goal that made it 2–2? | no data |
| u05 | Em quantos lances Mbappé ficou em posição de impedimento sem participar da jogada? | In how many plays was Mbappé in an offside position without taking part in the play? | no data |

In the sequences of three players, scoring is by set: the order is not checked.
In s04, only the second-half pair is checked. Besides
`check_ground_truth.py`, `scripts/check_cypher.py` answers the 47 questions
that have an answer with a hand-written Cypher query for each one, and all 47
agree with the ground truth. The questions file also has the stable reserves
and the removed questions, each with its reason. The computed answers are in
`data/benchmark/ground_truth.json`.

---

## 3.4 The golden rule of the ground truth: never read the database under test

The `graph_tools` arm queries Neo4j, and `stats_in_prompt` receives numbers
that come from Neo4j. If the ground truth also came from Neo4j, an error in the
database would show **on both sides**: the arm would be wrong, the ground truth
would be equally wrong, and the error would count as a right answer.

That is why the ground truth (`benchmark/ground_truth.py`) is computed along
**another path**:

1. **StatsBomb's raw JSON**, whenever the definition is simple:
   - goal = a `Shot` event with outcome `Goal`;
   - yellow card = a card inside `foul_committed` **or** `bad_behaviour`
     (Giroud's, for dissent, is in the second);
   - penalty = a foul marked as a penalty in `foul_committed`;
   - assist = a pass marked `goal_assist`;
   - completed take-on = a `Dribble` event with outcome `Complete`;
   - foul = a `Foul Committed` event; shot = a `Shot` event.

   The penalty shootout (period 5) is always excluded.

2. **The layer 0 table (Parquet)**, when the definition belongs to layer 0
   itself (successful tackle, pass with a receiver) and for everything about
   passing networks and sequences. The networks are computed with **networkx**,
   a Python graph library; the sequences, with pandas.

Checked against FIFA's official match report: 6 goals (at 23', 36', 80', 81',
108' and 118' broadcast time) and 7 yellow cards in open play. The 8th yellow,
Emiliano Martínez's, came in the shootout and is left out.

---

## 3.5 The robustness test: the same answer under every reading

A question in football language can be read in more than one way. Do "passes"
include throw-ins and set pieces? Does "after the goal" include the goal
itself? For each question, the ground truth computes the answer under **every
reasonable reading**:

| Axis | Readings | Where it applies |
|---|---|---|
| Set of passes | all completed passes · open-play passes only | everything that counts passes |
| Link weight | none · number of passes · xT | "main link" |
| Direction | passer → receiver · both directions added | pairs, links, teammates |
| Teammates | both directions · only those passed to · only those received from | "different teammates" |
| Time slice | with the event that defines the cut · without it | "after", "while" |
| Third | where the pass starts · where it ends | "in the final third" |
| Sequences | same possession or not · consecutive passes or not | "sequence of three" |
| Source | raw JSON · layer 0 | when both can serve |

A question stays only if **some answer is right under every reading**, in what
the scoring looks at: the player, the set or the number. A tie within one
reading does not disqualify: everyone tied at the top counts under that
reading. The accepted answer is the one at the top under all readings. Example:
"who passed the ball to Mbappé the most" gives Theo 8 × Rabiot 7 counting all
passes and 7 × 7 with open play only; Theo is at the top under both readings and
is the accepted answer, Rabiot is not. More than one accepted answer only
happens when they tie under every reading (p07). What removes a question is
readings that disagree with nobody at the top of all of them.

One example that went and one that stayed, both about "the main link in the
ball circulation":

| Question | Readings | Answers |
|---|---|---|
| Who was the main link in Argentina's ball circulation? | 12 | Otamendi in 9, Enzo Fernández in 3: **removed** |
| In extra time, who was the main link in France's ball circulation? | 12 | Koundé in all: **kept** |

Of the 81 questions written, 22 were removed by this test. Every reading of
every question is in
[`data/benchmark/robustness.md`](../data/benchmark/robustness.md), written by
`scripts/robustness_report.py`.

---

## 3.6 The network concepts, without formulas

For each team, a **passing network** is built:
- each player is a **node**;
- if A gave at least one completed pass to B, there is a **link A → B**;
- each link stores how many passes there were and how much xT they added in
  total.

The Mac Allister → Di María link, for example, includes the pass for the goal,
which added 0.184 xT.

On top of this network, the questions use four ideas:

**The pair that exchanged the most passes.** The strongest link, adding the two
directions of the pair or not.

**Different teammates.** How many colleagues a player exchanged at least one
pass with: the player's degree in the network.

**Main link in the circulation: betweenness.** Picture four players in a line,
where the ball only moves like this:

```
Goalkeeper → Center-back → Midfielder → Forward
```

To go from the Goalkeeper to the Forward, the ball **has** to go through the
Center-back and the Midfielder. If we count, for each pair of players, who sits
in the middle of the shortest path, the Center-back and the Midfielder show up
several times and the Goalkeeper and the Forward never. That count is
**betweenness**. Having many routes go through you is not the same as giving
many passes.

**The player without whom someone is isolated.** A player whose removal would
leave some teammate without exchanging passes with anyone is an **articulation
point** of the network. In the final, it is Otamendi: Pezzella, who came on late,
only exchanged passes with him.

**Sequence of three players.** A passes to B, and B, in the next pass he tries,
finds C. The readings vary whether the same possession and no other pass in
between are required.

Neo4j's GDS and networkx compute betweenness with the same convention (raw
values, not normalized), and the tests confirm that the two agree on all six
combinations of weight and direction.

---

## 3.7 Checking the ground truth against the graph

The ground truth was computed without Neo4j. To check it, each question is
answered again **through the `graph_tools` tools**, with a fixed sequence of
calls, no LLM:

```bash
python scripts/check_ground_truth.py           # the 52 active questions
python scripts/check_ground_truth.py --all     # the reserves too
```

Output (excerpt):

```
OK  s01  ground truth: ['Jules Koundé']  |  graph (tools): ['Jules Koundé']
OK  n09  ground truth: ['Dayotchanculle Upamecano', 'Jules Koundé', 'Raphaël Varane']  |  graph (tools): [...]
OK  u01  no data expected; the tools expose only on-ball events
...
52/52 agree
```

Since both sides were computed along independent paths, **the agreement
validates both at once**. It also shows that the tools are enough to answer
each question: every call sequence in the script is one possible solution.

---

## 3.8 How to change or add a question

1. Write the question in `config/questions.yaml`, following the rules in 3.2.
2. Add the answer function in `benchmark/ground_truth.py`, with every
   reasonable reading, and the equivalent call sequence in
   `scripts/check_ground_truth.py`.
3. Recompute and check:
   ```bash
   python -m football_graphrag.benchmark.ground_truth   # writes ground_truth.json
   python scripts/robustness_report.py                  # table of readings
   python scripts/check_ground_truth.py                 # must agree on all
   pytest tests/test_questions.py
   ```
4. If the answer changes with the reading, mark `stage: removed` and write the
   reason in `note`. The test fails if an active question is unstable.
