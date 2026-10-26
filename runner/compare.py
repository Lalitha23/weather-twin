"""Current versus candidate comparisons for the Live comparison view.

No Streamlit here, so it can be tested. Runs pass the scenario to the tool
directly, so several can run at once in one process. Lab runs are saved to
results/lab_<timestamp>.jsonl and never touch the official files.
"""
import json
import statistics
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agents.summarizer import PROMPTS, make_client
from checks.checks import CHECKS, run_checks
from runner.run_matrix import run_latency, run_tokens, scored_scenarios
from runner.run_once import run_one
from tools.weather_tool import TOOL_SPEC

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
LAB_CONFIG = ROOT / "config" / "lab.yaml"
OFFICIAL_FILES = {"matrix_summary.json", "official_matrix_oct25.jsonl"}
HIDDEN_MODEL_WORDS = ("embed", "image", "flux", "guard", "reward")
GROUPS = ("newly_broken", "fixed", "still_failing", "still_passing")
GROUP_TITLES = {"newly_broken": "Newly broken", "fixed": "Fixed",
                "still_failing": "Still failing", "still_passing": "Still passing"}


def lab_settings(path: Path = LAB_CONFIG) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def prompt_versions(prompts: Path = PROMPTS) -> list[str]:
    """Versions that have both a summarizer and an advisor prompt file."""
    summ = {p.stem.removeprefix("summarizer_") for p in prompts.glob("summarizer_*.md")}
    adv = {p.stem.removeprefix("advisor_") for p in prompts.glob("advisor_*.md")}
    return sorted(summ & adv)


def filter_models(ids: list[str]) -> list[str]:
    """Hide obvious non chat models and list Nemotron models first."""
    keep = [i for i in ids if not any(w in i.lower() for w in HIDDEN_MODEL_WORDS)]
    return sorted(keep, key=lambda i: ("nemotron" not in i.lower(), i.lower()))


def list_models(client=None) -> list[str]:
    client = client or make_client()
    return filter_models([m.id for m in client.models.list().data])


def tool_call_check(model: str, client=None) -> dict[str, Any]:
    """One cheap call: does this model make real tool calls?"""
    client = client or make_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "Use the get_weather tool to answer."},
                      {"role": "user", "content": "What's the weather right now?"}],
            tools=[TOOL_SPEC], tool_choice="auto", max_tokens=300, temperature=0)
    except Exception as e:  # recorded, never raised
        return {"ok": False, "label": "Unsupported · the check call failed. Skipped.",
                "reason": f"{type(e).__name__}: {e}"}
    msg = resp.choices[0].message
    if msg.tool_calls:
        return {"ok": True, "label": "Real tool calls work", "reason": ""}
    text = msg.content or ""
    if "get_weather" in text:
        return {"ok": False, "label": "Unsupported · wrote the tool call as text. Skipped.",
                "reason": text[:200]}
    return {"ok": False, "label": "Unsupported · made no tool call. Skipped.", "reason": text[:200]}


def official_tokens_per_run(summary: dict, model: str, prompt: str) -> tuple[float, bool]:
    """(tokens per run, measured). Unknown setups use the mean of all official columns."""
    for t in summary["totals"]:
        if t["model"] == model and t["prompt_version"] == prompt:
            return t["avg_total_tokens"], True
    return statistics.mean(t["avg_total_tokens"] for t in summary["totals"]), False


def estimate(setups: list[dict], scenarios: list[str], repeats: int, summary: dict) -> dict[str, Any]:
    per_setup = len(scenarios) * repeats
    tokens, guessed = 0.0, []
    for s in setups:
        per_run, measured = official_tokens_per_run(summary, s["model"], s["prompt_version"])
        tokens += per_run * per_setup
        if not measured:
            guessed.append(s["name"])
    return {"runs": per_setup * len(setups), "tokens": int(round(tokens, -3)), "guessed": guessed}


def jobs(setups: list[dict], scenarios: list[str], repeats: int) -> list[tuple[dict, str, int]]:
    """Interleaved: every setup runs a scenario and repeat before the next one starts,
    so current and candidates see the same load."""
    return [(s, sc, r) for sc in scenarios for r in range(1, repeats + 1) for s in setups]


def _rate_limited(line: dict) -> bool:
    errors = (line["summarizer"].get("error") or "") + (line["advisor"].get("error") or "")
    return "RateLimitError" in errors


def run_job(setup: dict, scenario: str, repeat: int, client, expected: dict,
            settings: dict, run_fn: Callable = run_one, sleep: Callable = time.sleep) -> dict:
    wait = settings["retry_wait_s"]
    for attempt in range(settings["rate_limit_retries"] + 1):
        line = run_fn(setup["model"], scenario, setup["prompt_version"], client)
        if not _rate_limited(line) or attempt == settings["rate_limit_retries"]:
            break
        sleep(wait)
        wait *= 2
    line.update({"setup": setup["key"], "repeat": repeat, "rate_limit_retries": attempt,
                 "checks": run_checks(line, expected)})
    return line


def run_comparison(setups: list[dict], scenarios: list[str], repeats: int, client=None,
                   settings: dict | None = None, run_fn: Callable = run_one
                   ) -> Iterator[tuple[int, int, dict]]:
    """Yield (done, total, line) as runs finish. Progress updates belong to the caller."""
    client = client or make_client()
    settings = settings or lab_settings()
    expected = scored_scenarios()
    todo = jobs(setups, scenarios, repeats)
    with ThreadPoolExecutor(max_workers=settings["workers"]) as pool:
        futures = [pool.submit(run_job, s, sc, r, client, expected[sc], settings, run_fn)
                   for s, sc, r in todo]
        for done, future in enumerate(as_completed(futures), start=1):
            yield done, len(todo), future.result()


def _counts(lines: list[dict], setup_key: str, scenario: str, check: str) -> dict[str, int]:
    results = [l["checks"][check]["result"] for l in lines
               if l["setup"] == setup_key and l["scenario"] == scenario]
    applicable = [r for r in results if r != "n/a"]
    return {"passed": applicable.count("pass"), "applicable": len(applicable)}


def _passes(count: dict) -> bool:
    """A cell passes only if every repeat passed."""
    return count["applicable"] > 0 and count["passed"] == count["applicable"]


def classify(lines: list[dict], current: str, candidate: str) -> dict[str, list[dict]]:
    """Sort every scenario x check cell into the four groups. Cells that do not
    apply on both sides are skipped (format_ok still catches a missing answer)."""
    groups: dict[str, list[dict]] = {g: [] for g in GROUPS}
    scenarios = list(dict.fromkeys(l["scenario"] for l in lines))
    for scenario in scenarios:
        for check in CHECKS:
            cur = _counts(lines, current, scenario, check)
            cand = _counts(lines, candidate, scenario, check)
            if not cur["applicable"] or not cand["applicable"]:
                continue
            was, now = _passes(cur), _passes(cand)
            group = ("still_passing" if was and now else "newly_broken" if was
                     else "fixed" if now else "still_failing")
            groups[group].append({"scenario": scenario, "check": check,
                                  "current": cur, "candidate": cand})
    return groups


def cost(lines: list[dict], setup_key: str) -> dict[str, float]:
    mine = [l for l in lines if l["setup"] == setup_key]
    if not mine:
        return {"avg_total_tokens": 0, "median_latency_s": 0}
    return {"avg_total_tokens": round(sum(map(run_tokens, mine)) / len(mine), 1),
            "median_latency_s": round(statistics.median(map(run_latency, mine)), 2)}


def save_lab_run(meta: dict, lines: list[dict], results: Path = RESULTS) -> Path:
    """Write results/lab_<timestamp>.jsonl: a meta line, then one line per run."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = results / f"lab_{stamp}.jsonl"
    assert path.name not in OFFICIAL_FILES
    results.mkdir(exist_ok=True)
    with path.open("x") as f:  # "x" never overwrites
        f.write(json.dumps({"meta": meta}) + "\n")
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def list_lab_runs(results: Path = RESULTS) -> list[Path]:
    return sorted(results.glob("lab_*.jsonl"), reverse=True)


def load_lab_run(path: Path) -> tuple[dict, list[dict]]:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return rows[0]["meta"], rows[1:]
