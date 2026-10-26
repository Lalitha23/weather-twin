"""Run Agent 1 then Agent 2 once and append one line to results/runs.jsonl.

Run from the repo root:
      python -m runner.run_once                    uses NEMOTRON_MODEL
      python -m runner.run_once --model compare    uses COMPARE_MODEL
      python -m runner.run_once --model <model-id>
      python -m runner.run_once --scenario snow         twin backend, that scenario
      python -m runner.run_once --prompt v2             hardened prompts
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from agents.advisor import run_advisor
from agents.summarizer import make_client, run_summarizer
from tools.weather_twin import SCENARIOS

RESULTS = Path(__file__).resolve().parent.parent / "results" / "runs.jsonl"
ALIASES = {"nemotron": "NEMOTRON_MODEL", "compare": "COMPARE_MODEL"}


def resolve_model(name: str) -> str:
    """nemotron or compare reads .env; anything else is a raw model ID."""
    model = os.getenv(ALIASES[name], "") if name in ALIASES else name
    if not model:
        sys.exit(f"{ALIASES[name]} is not set in .env.")
    return model


def check_scenario(name: str) -> None:
    if not (SCENARIOS / f"{name}.json").is_file():
        names = ", ".join(sorted(p.stem for p in SCENARIOS.glob("*.json")))
        sys.exit(f"Unknown scenario {name!r}. Choose from: {names}")


def run_one(model: str, scenario: str | None, prompt_version: str,
            client: OpenAI) -> dict[str, Any]:
    """Both agents once. A scenario runs on the twin, passed to the tool directly
    (safe across threads). scenario=None uses WEATHER_BACKEND as set."""
    weather = {"backend": "twin", "scenario": scenario} if scenario else None
    backend = "twin" if scenario else os.getenv("WEATHER_BACKEND", "live").strip().lower()
    summarizer = run_summarizer(model, client, prompt_version, weather)
    advisor = run_advisor(model, summarizer["summary"], client, prompt_version)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backend": backend,
        "scenario": scenario or "live",
        "model": model,
        "prompt_version": prompt_version,
        "summarizer": summarizer,
        "advisor": advisor,
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="nemotron",
                        help="nemotron, compare, or a raw model ID")
    parser.add_argument("--scenario", help="twin scenario name in scenarios/ (default: live)")
    parser.add_argument("--prompt", default="v1", choices=["v1", "v2"])
    args = parser.parse_args()

    if not os.getenv("NEBIUS_API_KEY"):
        sys.exit("NEBIUS_API_KEY is missing. Copy .env.example to .env and fill it in.")
    model = resolve_model(args.model)
    if args.scenario:
        check_scenario(args.scenario)

    line = run_one(model, args.scenario, args.prompt, make_client())
    RESULTS.parent.mkdir(exist_ok=True)
    with RESULTS.open("a") as f:
        f.write(json.dumps(line) + "\n")

    advisor, summarizer = line["advisor"], line["summarizer"]
    a = advisor["advice"] or {}
    errors = [e for e in (summarizer["error"], advisor["error"]) if e]
    print(f"{model}  [{line['scenario']} {args.prompt}]  jacket={a.get('jacket')} "
          f"umbrella={a.get('umbrella')} confident={a.get('confident')}  "
          f"errors: {', '.join(errors) or 'none'}  -> results/runs.jsonl")
    if advisor["advice"]:
        print(f"  why: {a['why']}")


if __name__ == "__main__":
    main()
