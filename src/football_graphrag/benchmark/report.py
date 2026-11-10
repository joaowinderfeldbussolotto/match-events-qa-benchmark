"""The page of one benchmark run, written to ``docs/runs/`` at the end of every run.

Pure function of ``results.jsonl`` plus a few facts about the run (command, commit,
cost): no LLM, no Neo4j. ``scripts/run_benchmark.py`` calls ``write_report`` when it
finishes; ``scripts/report_run.py`` writes the page again from an existing results file.
The page follows the hand-written ones: configuration, results by group and arm, kinds
of error, cost, an automatic reading of the numbers, every miss with its expected
answer, and the traces. It also adds the run to the index (``docs/runs/README.md``).
"""

import json
import re
import subprocess
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from statistics import mean

from football_graphrag.benchmark.arms import ARMS
from football_graphrag.benchmark.questions import BY_ID, GROUP_OF, GROUPS, ORDER

RUNS_DIR = Path(__file__).resolve().parents[3] / "docs" / "runs"
CONTROL = "Control: no answer"
ICONS = {"ok": "✅", "wrong": "❌", "abstention": "🟡", "format_error": "⚠️"}
VERDICT = {"wrong": "hallucination", "abstention": "abstention", "format_error": "format error"}


@dataclass
class RunInfo:
    command: str = ""
    cost_usd: float | None = None
    day: date = field(default_factory=date.today)
    failed: int = 0  # provider errors, not written to the results file


def openrouter_usage(api_key: str) -> float | None:
    """Total spent by the key, in US$ (``usage`` of /api/v1/key); None if unavailable."""
    if not api_key:
        return None
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                     headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return float(json.load(resp)["data"]["usage"])
    except Exception:
        return None


def git_revision() -> str:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, cwd=RUNS_DIR).stdout.strip()
    commit, branch = git("rev-parse", "--short", "HEAD"), git("branch", "--show-current")
    if not commit:
        return "unknown"
    # The run itself writes results and pages: only code changes make the revision dirty.
    dirty = " (with uncommitted changes)" if git("status", "--porcelain", "--untracked-files=no", "--", ":/",
                                                    ":!/data", ":!/docs/runs") else ""
    return f"branch `{branch}`, commit `{commit}`{dirty}"


def verdict(row: dict) -> str:
    if row["correct"]:
        return "ok"
    return "format_error" if row["format_error"] else "abstention" if row["abstention"] else "wrong"


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows])


def _count(rows: list[dict]) -> str:
    return f"{sum(r['correct'] for r in rows)}/{len(rows)} ({100 * mean(r['correct'] for r in rows):.0f}%)" if rows else "–"


def _expected(e: dict) -> str:
    if e.get("no_data"):
        return "no data"
    options = e.get("accepted") or ([e["players"]] if e.get("players") else [])
    parts = [" or ".join(", ".join(o) for o in options)] if options else []
    if e.get("value") is not None:
        parts.append(f"{e['value']:g}")
    return " · ".join(parts) or "–"


def _answer(a: dict | None) -> str:
    if a is None:
        return "no valid answer"
    if a.get("no_data"):
        return "no data"
    parts = [", ".join(a["players"])] if a.get("players") else []
    if a.get("value") is not None:
        parts.append(f"{a['value']:g}")
    return " · ".join(parts) or "–"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def reading(rows: list[dict], arms: list[str]) -> list[str]:
    """The automatic reading: plain facts computed from the rows, no interpretation."""
    by_arm = {a: [r for r in rows if r["arm"] == a] for a in arms}
    answerable = {a: [r for r in rs if r["type"] != "unanswerable"] for a, rs in by_arm.items()}
    acc = {a: mean(r["correct"] for r in rs) for a, rs in answerable.items() if rs}
    out = []
    if acc:
        ranked = sorted(acc, key=acc.get, reverse=True)
        out.append("**Arm order** (without the questions that have no answer): "
                   + " > ".join(f"`{a}` {100 * acc[a]:.0f}%" for a in ranked) + ".")
        if len(ranked) > 1:
            gap = 100 * (acc[ranked[0]] - acc[ranked[1]])
            out.append(f"**Gap between the first and the second:** {gap:.0f} percentage points.")
    for g, types in GROUPS.items():
        if g == CONTROL:
            continue
        scores = {a: [r["correct"] for r in by_arm[a] if r["type"] in types] for a in arms}
        scores = {a: mean(v) for a, v in scores.items() if v}
        if not scores:
            continue
        best = max(scores.values())
        leaders = [a for a, v in scores.items() if v == best]
        out.append(f"**{g}:** best {', '.join(f'`{a}`' for a in leaders)} ({100 * best:.0f}%); "
                   + ", ".join(f"`{a}` {100 * v:.0f}%" for a, v in scores.items() if a not in leaders) + ".")
    per_q = defaultdict(dict)
    for r in rows:
        per_q[r["question_id"]].setdefault(r["arm"], []).append(r["correct"])
    q_order = sorted(per_q, key=lambda q: (ORDER.index(q[0]), q))
    nobody = [q for q in q_order if not any(any(v) for v in per_q[q].values())]
    if nobody:
        out.append(f"**No arm got it right** ({len(nobody)}): {', '.join(nobody)}.")
    for a in arms:
        only = [q for q in q_order if any(per_q[q].get(a, []))
                and not any(any(v) for b, v in per_q[q].items() if b != a)]
        if only and len(arms) > 1:
            out.append(f"**Only `{a}` got it right** ({len(only)}): {', '.join(only)}.")
    for a in arms:
        rs = by_arm[a]
        kinds = defaultdict(int)
        for r in rs:
            if not r["correct"]:
                kinds[verdict(r)] += 1
        if kinds:
            main = max(kinds, key=kinds.get)
            out.append(f"**`{a}` misses mostly by {VERDICT[main]}:** "
                       + ", ".join(f"{n} {VERDICT[k]}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])) + ".")
    return ["- " + line for line in out]


def render(rows: list[dict], number: int, title: str, info: RunInfo, results_path: str,
           summary_path: str, revision: str) -> str:
    arms = [a for a in ARMS if any(r["arm"] == a for r in rows)]
    by_arm = {a: [r for r in rows if r["arm"] == a] for a in arms}
    qids = sorted({r["question_id"] for r in rows}, key=lambda q: (ORDER.index(q[0]), q))
    repeats = sorted({int(r["repeat"]) for r in rows})
    models = sorted({r["model"] for r in rows})
    cost = f"US$ {info.cost_usd:.2f} (OpenRouter key usage before and after)" if info.cost_usd is not None \
        else "not measured"
    out = [
        f"# Run {number:02d}: {title}",
        "",
        "Page written automatically by `scripts/run_benchmark.py` (or `scripts/report_run.py`) from the "
        "results file. The numbers are counts of runs, scored by code against `ground_truth.json`.",
        "",
        _table(["", ""], [
            ["Date", info.day.isoformat()],
            ["Scope", f"{len(qids)} questions × {len(arms)} arms ({', '.join(f'`{a}`' for a in arms)}) × "
                      f"{len(repeats)} repeat(s) = {len(rows)} runs"],
            ["Model", ", ".join(f"`{m}`" for m in models)],
            ["Code", revision],
            ["Command", f"`{info.command}`" if info.command else "–"],
            ["Real cost", cost],
            ["Files", f"[`{Path(results_path).name}`]({results_path}), [`{Path(summary_path).name}`]({summary_path})"],
        ]),
    ]
    if info.failed:
        out += ["", f"> **{info.failed} runs failed with a provider error** and are not in the file; "
                    "run again with `--resume`."]

    body = []
    for g, types in GROUPS.items():
        n = len({r["question_id"] for r in rows if r["type"] in types})
        if n:
            body.append([g, str(n)] + [_count([r for r in by_arm[a] if r["type"] in types]) for a in arms])
    body.append(["**total**", str(len(qids))] + [f"**{_count(by_arm[a])}**" for a in arms])
    body.append(["**total without the control**", str(len({r['question_id'] for r in rows if r['type'] != 'unanswerable'}))]
                + [f"**{_count([r for r in by_arm[a] if r['type'] != 'unanswerable'])}**" for a in arms])
    out += ["", "## Results by group", "",
            "The control group (questions the data cannot answer) is won by an arm that answers \"no data\" "
            "to everything; the last row leaves it out.", "", _table(["group", "questions"] + arms, body)]

    body = []
    for a in arms:
        rs = by_arm[a]
        kinds = [verdict(r) for r in rs]
        body.append([f"`{a}`"] + [f"{100 * kinds.count(k) / len(rs):.0f}%" for k in ("wrong", "abstention", "format_error")]
                    + [f"{mean(r['input_tokens'] for r in rs):,.0f}".replace(",", "."),
                       f"{mean(r['output_tokens'] for r in rs):,.0f}".replace(",", "."),
                       f"{mean(r['n_tool_calls'] for r in rs):.1f}", f"{mean(r['latency_s'] for r in rs):.1f} s"])
    out += ["", "## Errors and cost by arm", "",
            "Hallucination: a wrong answer given as an answer. Abstention: \"no data\" on a question that has "
            "an answer. Format error: no valid answer after the retries (or the call limit was reached).",
            "", _table(["arm", "hallucination", "abstention", "format error", "input tokens", "output tokens",
                        "tool calls", "latency"], body)]

    out += ["", "## Automatic reading", "", *reading(rows, arms)]

    out += ["", "## Misses of each arm", ""]
    for a in arms:
        misses = sorted((r for r in by_arm[a] if not r["correct"]),
                        key=lambda r: (ORDER.index(r["question_id"][0]), r["question_id"], int(r["repeat"])))
        if not misses:
            out += [f"**`{a}`:** no misses.", ""]
            continue
        lines = [[f"[{r['question_id']}]({r['trace_url']})" if r.get("trace_url") else r["question_id"],
                  _cell(BY_ID[r["question_id"]].text if r["question_id"] in BY_ID else ""),
                  _cell(_expected(r["expected"])), _cell(_answer(r["answer"])), VERDICT[verdict(r)]]
                 for r in misses]
        out += [f"<details><summary><b><code>{a}</code></b>: {len(misses)} misses</summary>", "",
                _table(["question", "text", "expected", "answer", "kind"], lines), "", "</details>", ""]

    body = []
    for q in qids:
        cells = []
        for a in arms:
            rs = sorted((r for r in by_arm[a] if r["question_id"] == q), key=lambda r: int(r["repeat"]))
            cells.append(" ".join(f"[{ICONS[verdict(r)]}]({r['trace_url']})" if r.get("trace_url")
                                  else ICONS[verdict(r)] for r in rs) or "–")
        body.append([q, GROUP_OF.get(BY_ID[q].type, "") if q in BY_ID else ""] + cells)
    out += ["## Traces", "", _table(["question", "group"] + [f"`{a}`" for a in arms], body), "",
            "✅ right · ❌ hallucination · 🟡 abstention · ⚠️ format error. Each symbol opens the trace in "
            "Langfuse; the Langfuse project is private, so the links only open for its members.", ""]
    return "\n".join(out)


def next_number(runs_dir: Path = RUNS_DIR) -> int:
    numbers = [int(m.group(1)) for p in runs_dir.glob("*.md") if (m := re.match(r"\d{4}-\d{2}-\d{2}_(\d+)_", p.name))]
    return max(numbers, default=0) + 1


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-")


def index_row(number: int, page: str, info: RunInfo, title: str, rows: list[dict]) -> str:
    models = ", ".join(sorted({r["model"].split(":", 1)[-1].split("/")[-1] for r in rows}))
    graph = [r for r in rows if r["arm"] == "graph_tools"]
    graph_acc = f"{sum(r['correct'] for r in graph)}/{len(graph)}" if graph else "–"
    cost = f"US$ {info.cost_usd:.2f}" if info.cost_usd is not None else "–"
    return f"| [{number:02d}]({page}) | {info.day.isoformat()} | {title} | {models} | {len(rows)} | {graph_acc} | {cost} |"


def add_to_index(row: str, runs_dir: Path = RUNS_DIR) -> None:
    """Insert the row after the last row of the index table."""
    index = runs_dir / "README.md"
    if not index.exists():
        return
    lines = index.read_text().splitlines()
    last = max((i for i, line in enumerate(lines) if re.match(r"\| \[\d+\]\(", line)), default=None)
    if last is None:
        return
    lines.insert(last + 1, row)
    index.write_text("\n".join(lines) + "\n")


def _previous(page: Path) -> tuple[str, str, float | None]:
    """Title, command and cost recorded on an existing run page."""
    text = page.read_text()
    title = re.search(r"^# Run \d+: (.*)$", text, re.M)
    command = re.search(r"^\| Command \| (.*) \|$", text, re.M)
    cost = re.search(r"^\| Real cost \| US\$ ([\d.]+)", text, re.M)
    return (title.group(1) if title else "", command.group(1).strip("`") if command else "",
            float(cost.group(1)) if cost else None)


def replace_in_index(number: int, row: str, runs_dir: Path = RUNS_DIR) -> None:
    index = runs_dir / "README.md"
    if not index.exists():
        return
    lines = [row if line.startswith(f"| [{number:02d}](") else line for line in index.read_text().splitlines()]
    index.write_text("\n".join(lines) + "\n")


def write_report(results_path: Path, summary_path: Path, info: RunInfo, title: str | None = None,
                 runs_dir: Path = RUNS_DIR, page: Path | None = None) -> Path:
    """Write a new run page, or rewrite ``page`` (an earlier page of the same results file):
    same number and date, its cost plus this one, its command followed by this one."""
    from football_graphrag.benchmark.summary import load_rows

    rows = load_rows(results_path)
    arms = [a for a in ARMS if any(r["arm"] == a for r in rows)]
    if page is not None:
        page = Path(page)
        number, day = int(page.name.split("_")[1]), date.fromisoformat(page.name.split("_")[0])
        old_title, old_command, old_cost = _previous(page)
        cost = old_cost + info.cost_usd if old_cost is not None and info.cost_usd is not None else None
        command = f"{old_command}`, then `{info.command}" if old_command else info.command
        info = RunInfo(command=command, cost_usd=cost, day=day, failed=info.failed)
        title = title or old_title
    else:
        number = next_number(runs_dir)
    title = title or f"{len({r['question_id'] for r in rows})} questions, {len(arms)} arms"
    new_page = page is None
    page = page or runs_dir / f"{info.day.isoformat()}_{number:02d}_{_slug(results_path.stem.removesuffix('_results'))}.md"

    def rel(p: Path) -> str:
        try:
            return str(Path("../..") / p.resolve().relative_to(runs_dir.resolve().parents[1]))
        except ValueError:
            return str(p)
    page.write_text(render(rows, number, title, info, rel(results_path), rel(summary_path), git_revision()))
    row = index_row(number, page.name, info, title, rows)
    add_to_index(row, runs_dir) if new_page else replace_in_index(number, row, runs_dir)
    return page
