"""Run Agent 1 (summarizer) once and print the full result.

Run:  python scripts/check_summarizer.py                    uses NEMOTRON_MODEL
      python scripts/check_summarizer.py --model compare    uses COMPARE_MODEL
      python scripts/check_summarizer.py --model <model-id>
Follows WEATHER_BACKEND from .env.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.summarizer import run_summarizer  # noqa: E402

load_dotenv()

ALIASES = {"nemotron": "NEMOTRON_MODEL", "compare": "COMPARE_MODEL"}

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="nemotron",
                    help="nemotron, compare, or a raw model ID")
args = parser.parse_args()

if not os.getenv("NEBIUS_API_KEY"):
    sys.exit("NEBIUS_API_KEY is missing. Copy .env.example to .env and fill it in.")

model = os.getenv(ALIASES[args.model], "") if args.model in ALIASES else args.model
if not model:
    sys.exit(f"{ALIASES[args.model]} is not set in .env.")

print(json.dumps(run_summarizer(model), indent=2))
