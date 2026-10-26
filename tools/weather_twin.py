"""Twin weather backend: replays a scenario file instead of calling Open-Meteo.

The scenario is passed in, or named by WEATHER_SCENARIO (a file in scenarios/, without .json). The file is a
raw Open-Meteo response, run through the same parse() as the live backend.
A "_twin": {"simulate": "timeout"} key makes it raise requests.Timeout, so
the tool returns the same error the live backend gives on a real timeout.
"_twin": {"overrides": {...}} replaces parsed fields after parse(), to
simulate a tampered upstream response. The agents never see _twin.
"""
import json
import os
from pathlib import Path
from typing import Any

import requests

from tools.weather_live import parse

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def load_scenario(name: str | None = None) -> dict[str, Any]:
    """Load a scenario by name, or the one in WEATHER_SCENARIO. Setup mistakes raise."""
    name = (name or os.getenv("WEATHER_SCENARIO", "")).strip()
    if not name:
        raise RuntimeError("WEATHER_SCENARIO is not set. Name a file in scenarios/.")
    path = SCENARIOS / f"{name}.json"
    if not path.is_file():
        raise RuntimeError(f"Scenario file not found: {path}")
    return json.loads(path.read_text())


def get_weather_twin(scenario: str | None = None) -> dict[str, Any]:
    raw = load_scenario(scenario)
    twin = raw.get("_twin") or {}
    if twin.get("simulate") == "timeout":
        raise requests.Timeout("simulated timeout")
    return {**parse(raw), **twin.get("overrides", {})}
