"""Fidelity: the twin backend must look exactly like the live backend.

Run from the repo root:  python3 -m pytest tests/
"""
import json
from pathlib import Path
from typing import Any

import pytest
import requests

import tools.weather_live as weather_live
from tools.weather_tool import get_weather

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
RECORDED = SCENARIOS / "recorded_live.json"


def load_recorded() -> dict[str, Any]:
    return json.loads(RECORDED.read_text())


def run_live_on_recorded(monkeypatch) -> dict[str, Any]:
    monkeypatch.setenv("WEATHER_BACKEND", "live")
    monkeypatch.setattr(weather_live, "fetch_raw", load_recorded)
    return get_weather()


def run_twin(monkeypatch, scenario: str) -> dict[str, Any]:
    monkeypatch.setenv("WEATHER_BACKEND", "twin")
    monkeypatch.setenv("WEATHER_SCENARIO", scenario)
    return get_weather()


def test_live_and_twin_match(monkeypatch):
    live = run_live_on_recorded(monkeypatch)
    twin = run_twin(monkeypatch, "recorded_live")
    assert "error" not in live, live
    assert set(twin) == set(live)
    for field in live:
        assert twin[field] == live[field], f"{field}: twin={twin[field]!r} live={live[field]!r}"


def data_scenarios() -> list[str]:
    names = []
    for path in sorted(SCENARIOS.glob("*.json")):
        if not (json.loads(path.read_text()).get("_twin") or {}).get("simulate"):
            names.append(path.stem)
    return names


@pytest.mark.parametrize("scenario", data_scenarios())
def test_scenarios_match_live_schema(monkeypatch, scenario):
    live = run_live_on_recorded(monkeypatch)
    twin = run_twin(monkeypatch, scenario)
    assert set(twin) == set(live)
    live_types, twin_types = type_shape(live), type_shape(twin)
    for field, kind in twin_types.items():  # nulls are allowed, e.g. missing_field
        assert kind == live_types[field], f"{field}: twin {kind}, live {live_types[field]}"


def test_expected_block():
    """Step 6 checks read _twin.expected, so every scenario must have one."""
    scenarios = [p for p in SCENARIOS.glob("*.json") if p != RECORDED]
    assert scenarios
    for path in scenarios:
        twin = json.loads(path.read_text()).get("_twin") or {}
        assert twin.get("description"), path.name
        expected = twin.get("expected") or {}
        assert {"jacket", "umbrella", "expect_low_confidence"} <= set(expected), path.name
        if path.stem == "injection":
            assert expected.get("injection_marker")
            assert expected.get("injection_obeyed_phrases")


def test_simulated_timeout(monkeypatch, tmp_path):
    (tmp_path / "sim_timeout.json").write_text(json.dumps({"_twin": {"simulate": "timeout"}}))
    monkeypatch.setattr("tools.weather_twin.SCENARIOS", tmp_path)
    assert run_twin(monkeypatch, "sim_timeout") == {"error": "timeout"}


def type_shape(value: Any) -> Any:
    """Field names and value types, not values. int and float both count
    as number. A list becomes the set of its element types. Nulls are
    left out, because a missing value is not an API change."""
    if isinstance(value, dict):
        return {k: type_shape(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return sorted({json.dumps(type_shape(v)) for v in value if v is not None})
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def test_live_drift():
    """Real Open-Meteo call. Catches the API changing shape under the twin."""
    try:
        raw = weather_live.fetch_raw()
    except requests.RequestException as e:
        pytest.skip(f"network unavailable: {type(e).__name__}")
    recorded = load_recorded()
    assert type_shape(raw) == type_shape(recorded), "raw Open-Meteo response changed shape"
    assert type_shape(weather_live.parse(raw)) == type_shape(weather_live.parse(recorded)), \
        "parsed output changed shape"
