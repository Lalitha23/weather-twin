"""Twin weather backend: replays a scenario file instead of calling Open-Meteo.

WEATHER_SCENARIO names a file in scenarios/ (without .json). The file is a
raw Open-Meteo response, run through the same parse() as the live backend.
A "_twin": {"simulate": "timeout"} key makes it raise requests.Timeout, so
the tool returns the same error the live backend gives on a real timeout.
"""
import json
import os
from pathlib import Path
from typing import Any

import requests

from tools.weather_live import parse

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def load_scenario() -> dict[str, Any]:
    """Load the scenario named by WEATHER_SCENARIO. Setup mistakes raise."""
    name = os.getenv("WEATHER_SCENARIO", "").strip()
    if not name:
        raise RuntimeError("WEATHER_SCENARIO is not set. Name a file in scenarios/.")
    path = SCENARIOS / f"{name}.json"
    if not path.is_file():
        raise RuntimeError(f"Scenario file not found: {path}")
    return json.loads(path.read_text())


def get_weather_twin() -> dict[str, Any]:
    raw = load_scenario()
    if (raw.get("_twin") or {}).get("simulate") == "timeout":
        raise requests.Timeout("simulated timeout")
    return parse(raw)
