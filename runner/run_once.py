"""Run Agent 1 then Agent 2 once and append one line to results/runs.jsonl.

Run from the repo root:
      python -m runner.run_once                    uses NEMOTRON_MODEL
      python -m runner.run_once --model compare    uses COMPARE_MODEL
      python -m runner.run_once --model <model-id>
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from agents.advisor import run_advisor
from agents.summarizer import make_client, run_summarizer

RESULTS = Path(__file__).resolve().parent.parent / "results" / "runs.jsonl"
ALIASES = {"nemotron": "NEMOTRON_MODEL", "compare": "COMPARE_MODEL"}


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="nemotron",
                        help="nemotron, compare, or a raw model ID")
    args = parser.parse_args()

    if not os.getenv("NEBIUS_API_KEY"):
        sys.exit("NEBIUS_API_KEY is missing. Copy .env.example to .env and fill it in.")
    model = os.getenv(ALIASES[args.model], "") if args.model in ALIASES else args.model
    if not model:
        sys.exit(f"{ALIASES[args.model]} is not set in .env.")

    client = make_client()
    summarizer = run_summarizer(model, client)
    advisor = run_advisor(model, summarizer["summary"], client)

    line = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backend": os.getenv("WEATHER_BACKEND", "live").strip().lower(),
        "scenario": "live",
        "model": model,
        "summarizer": summarizer,
        "advisor": advisor,
    }
    RESULTS.parent.mkdir(exist_ok=True)
    with RESULTS.open("a") as f:
        f.write(json.dumps(line) + "\n")

    a = advisor["advice"] or {}
    errors = [e for e in (summarizer["error"], advisor["error"]) if e]
    print(f"{model}  jacket={a.get('jacket')} umbrella={a.get('umbrella')} "
          f"confident={a.get('confident')}  errors: {', '.join(errors) or 'none'}  "
          "-> results/runs.jsonl")
    if advisor["advice"]:
        print(f"  why: {a['why']}")


if __name__ == "__main__":
    main()
