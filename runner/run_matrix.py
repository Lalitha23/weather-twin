"""Run every scenario x model x prompt version, 3 times each, and score them.

Run from the repo root:
      python -m runner.run_matrix
      python -m runner.run_matrix --models nemotron --prompts v2 --scenarios snow --repeats 1
      python -m runner.run_matrix --rescore    recompute checks on saved runs, no model calls
      python -m runner.run_matrix --rescore --official --force    rescore the official run

By default it writes scratch files only: each run appends one line (with
check results) to results/matrix_scratch.jsonl, and the summary goes to
results/matrix_scratch_summary.json. The official files the app deploys from
(official_matrix_oct25.jsonl and matrix_summary.json) are written only with
--official, which refuses if the official runs file exists unless --force.
Runs are sequential, as in the official run.
"""
import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agents.summarizer import make_client
from checks.checks import CHECKS, run_checks
from runner.run_once import ALIASES, resolve_model, run_one
from tools.weather_twin import SCENARIOS

RESULTS = Path(__file__).resolve().parent.parent / "results"
SCRATCH = ("matrix_scratch.jsonl", "matrix_scratch_summary.json")
OFFICIAL = ("official_matrix_oct25.jsonl", "matrix_summary.json")


def output_paths(official: bool, force: bool) -> tuple[Path, Path]:
    """(runs file, summary file). The official pair needs --official, and
    --force as well once the official runs file exists."""
    runs, summary = (RESULTS / n for n in (OFFICIAL if official else SCRATCH))
    if official and runs.exists() and not force:
        sys.exit(f"{runs.name} already exists. It is the official run. "
                 "Add --force to overwrite it and matrix_summary.json.")
    return runs, summary


def _shown(path: Path) -> str:
    return os.path.relpath(path, RESULTS.parent)


def scored_scenarios() -> dict[str, dict]:
    """Scenario name -> _twin.expected, for every file that has one."""
    out = {}
    for path in sorted(SCENARIOS.glob("*.json")):
        expected = (json.loads(path.read_text()).get("_twin") or {}).get("expected")
        if expected:
            out[path.stem] = expected
    return out


def run_tokens(line: dict) -> int:
    return line["summarizer"]["usage"]["total_tokens"] + line["advisor"]["usage"]["total_tokens"]


def run_latency(line: dict) -> float:
    return (line["summarizer"]["latency_s"] or 0) + (line["advisor"]["latency_s"] or 0)


def tally(lines: list[dict]) -> dict[str, Any]:
    """Pass counts per check plus average tokens and latency over lines."""
    checks = {}
    for name in CHECKS:
        results = [l["checks"][name]["result"] for l in lines]
        applicable = [r for r in results if r != "n/a"]
        checks[name] = {"passed": applicable.count("pass"), "applicable": len(applicable)}
    n = len(lines) or 1
    return {
        "runs": len(lines),
        "checks": checks,
        "avg_total_tokens": round(sum(map(run_tokens, lines)) / n, 1),
        "avg_latency_s": round(sum(map(run_latency, lines)) / n, 2),
        "median_latency_s": round(statistics.median(map(run_latency, lines)), 2) if lines else 0,
    }


def summarize(lines: list[dict], columns: list[tuple[str, str, str]],
              scenarios: list[str], repeats: int) -> dict[str, Any]:
    """columns are (label, model_id, prompt_version)."""
    def pick(model: str, prompt: str, scenario: str | None = None) -> list[dict]:
        return [l for l in lines if l["model"] == model and l["prompt_version"] == prompt
                and (scenario is None or l["scenario"] == scenario)]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repeats": repeats,
        "columns": [{"label": c, "model": m, "prompt_version": p} for c, m, p in columns],
        "cells": [{"scenario": s, "column": c, "model": m, "prompt_version": p, **tally(pick(m, p, s))}
                  for s in scenarios for c, m, p in columns],
        "totals": [{"column": c, "model": m, "prompt_version": p, **tally(pick(m, p))}
                   for c, m, p in columns],
    }


def fmt(count: dict) -> str:
    return f"{count['passed']} of {count['applicable']}" if count["applicable"] else "-"


def print_table(summary: dict) -> None:
    labels = [c["label"] for c in summary["columns"]]
    width = max(len(l) for l in labels + ["3 of 3"]) + 2
    head = f"{'scenario':22}{'check':24}" + "".join(f"{l:>{width}}" for l in labels)
    print("\n" + head + "\n" + "-" * len(head))
    by_scenario: dict[str, dict[str, dict]] = {}
    for cell in summary["cells"]:
        by_scenario.setdefault(cell["scenario"], {})[cell["column"]] = cell
    for scenario, cells in by_scenario.items():
        first = True
        for name in CHECKS:
            row = [cells[l]["checks"][name] for l in labels]
            if not any(c["applicable"] for c in row):
                continue
            print(f"{scenario if first else '':22}{name:24}" + "".join(f"{fmt(c):>{width}}" for c in row))
            first = False
    print("-" * len(head))
    totals = {t["column"]: t for t in summary["totals"]}
    for name in CHECKS:
        print(f"{'TOTAL':22}{name:24}" + "".join(f"{fmt(totals[l]['checks'][name]):>{width}}" for l in labels))
    print(f"{'':22}{'avg total tokens':24}" + "".join(f"{totals[l]['avg_total_tokens']:>{width}}" for l in labels))
    print(f"{'':22}{'avg latency (s)':24}" + "".join(f"{totals[l]['avg_latency_s']:>{width}}" for l in labels))
    print(f"{'':22}{'median latency (s)':24}" + "".join(f"{totals[l]['median_latency_s']:>{width}}" for l in labels))


def finish(lines: list[dict], columns: list[tuple[str, str, str]],
           scenarios: list[str], repeats: int, runs_file: Path, summary_file: Path) -> None:
    summary = summarize(lines, columns, scenarios, repeats)
    summary_file.write_text(json.dumps(summary, indent=2) + "\n")
    print_table(summary)
    print(f"\nRuns -> {_shown(runs_file)}, summary -> {_shown(summary_file)}")


def rescore(all_scenarios: dict[str, dict], runs_file: Path, summary_file: Path) -> None:
    """Recompute every check on the saved runs and rewrite the runs file."""
    if not runs_file.exists():
        sys.exit(f"No runs file at {_shown(runs_file)}.")
    lines = [json.loads(l) for l in runs_file.read_text().splitlines() if l.strip()]
    if not lines:
        sys.exit(f"No runs in {_shown(runs_file)}.")
    for line in lines:
        line["checks"] = run_checks(line, all_scenarios[line["scenario"]])
    tmp = runs_file.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(l) + "\n" for l in lines))
    tmp.replace(runs_file)

    alias = {os.getenv(env): name for name, env in ALIASES.items()}
    columns = list(dict.fromkeys(
        (f"{alias.get(l['model'], l['model'])} {l['prompt_version']}", l["model"], l["prompt_version"])
        for l in lines))
    scenarios = list(dict.fromkeys(l["scenario"] for l in lines))
    finish(lines, columns, scenarios, max(l["repeat"] for l in lines), runs_file, summary_file)


def main() -> None:
    load_dotenv()
    all_scenarios = scored_scenarios()
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["nemotron", "compare"])
    parser.add_argument("--prompts", nargs="+", default=["v1", "v2"], choices=["v1", "v2"])
    parser.add_argument("--scenarios", nargs="+", default=list(all_scenarios),
                        choices=list(all_scenarios))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--rescore", action="store_true",
                        help="recompute checks on the saved runs without calling models")
    parser.add_argument("--official", action="store_true",
                        help="write the official files instead of the scratch files")
    parser.add_argument("--force", action="store_true",
                        help="with --official, overwrite the existing official run")
    args = parser.parse_args()
    runs_file, summary_file = output_paths(args.official, args.force)

    if args.rescore:
        rescore(all_scenarios, runs_file, summary_file)
        return

    if not os.getenv("NEBIUS_API_KEY"):
        sys.exit("NEBIUS_API_KEY is missing. Copy .env.example to .env and fill it in.")
    columns = [(f"{name} {p}", resolve_model(name), p) for name in args.models for p in args.prompts]
    client = make_client()
    total = len(args.scenarios) * len(columns) * args.repeats
    lines: list[dict] = []
    RESULTS.mkdir(exist_ok=True)

    # A new official run replaces the old one; scratch runs accumulate.
    with runs_file.open("w" if args.official else "a") as f:
        for scenario in args.scenarios:
            expected = all_scenarios[scenario]
            for label, model, prompt in columns:
                for repeat in range(1, args.repeats + 1):
                    line = run_one(model, scenario, prompt, client)
                    line["repeat"] = repeat
                    line["checks"] = run_checks(line, expected)
                    f.write(json.dumps(line) + "\n")
                    f.flush()
                    lines.append(line)
                    fails = [n for n, c in line["checks"].items() if c["result"] == "fail"]
                    print(f"[{len(lines):>3}/{total}] {scenario:22} {label:14} #{repeat}  "
                          f"fails: {', '.join(fails) or 'none'}", flush=True)

    finish(lines, columns, args.scenarios, args.repeats, runs_file, summary_file)


if __name__ == "__main__":
    main()
