"""Today's answer card words and the rules badge (display logic mirroring umbrella_rule and jacket_rule)."""
import pytest

from app.answer import MATCH, MISMATCH, UNKNOWN, answer_lines, rules_badge, weather_time
from app.xray import answer_card, today_html

TOOL = {"temperature_c": 10.9, "rain_chance_pct": 18, "wind_kph": 8.4, "conditions": "overcast",
        "time_of_day": "morning", "observed_at": "2026-10-26T11:23"}


def advice(jacket=False, umbrella=False, confident=True):
    return {"jacket": jacket, "umbrella": umbrella, "why": "Agent 2's own words.", "confident": confident}


def test_answer_lines():
    assert answer_lines(advice()) == ("No jacket.", "No umbrella.")
    assert answer_lines(advice(True, True)) == ("Take a jacket.", "Take an umbrella.")


def test_rules_match():
    assert rules_badge(TOOL, advice())["text"] == MATCH


@pytest.mark.parametrize("tool,adv,why", [
    ({**TOOL, "rain_chance_pct": 60}, advice(), "rain 60% is over 50%, so umbrella"),
    ({**TOOL, "temperature_c": 4}, advice(), "4 °C is under 10 °C, so jacket"),
    (TOOL, advice(umbrella=True), "rain 18% is not over 50%, so no umbrella"),
])
def test_rules_mismatch_says_which_rule(tool, adv, why):
    badge = rules_badge(tool, adv)
    assert badge["state"] == "mismatch" and badge["text"] == MISMATCH and badge["why"] == [why]


def test_rules_use_strict_limits():
    assert rules_badge({**TOOL, "rain_chance_pct": 50, "temperature_c": 10}, advice())["state"] == "match"


@pytest.mark.parametrize("tool,adv", [
    ({**TOOL, "temperature_c": None}, advice()),
    ({**TOOL, "rain_chance_pct": None}, advice()),
    ({"error": "timeout"}, advice()),
    (None, advice()),
    (TOOL, None),
])
def test_rules_cant_be_checked_on_incomplete_data(tool, adv):
    assert rules_badge(tool, adv) == {"state": "unknown", "text": UNKNOWN, "why": []}


def test_weather_time_from_observed_at():
    assert weather_time("2026-10-26T11:23") == "Mon · weather at 11:23"
    assert weather_time(None) is None and weather_time("soon") is None


def run(**overrides):
    r = {"tool": TOOL, "summary": {**TOOL, "data_ok": True, "notes": ""}, "advice": advice(),
         "numbers": {"result": "pass", "detail": ""},
         "agent1": {"model": "nvidia/Nemotron", "prompt_version": "v2"},
         "agent2": {"model": "nvidia/Nemotron", "prompt_version": "v2"}}
    return {**r, **overrides}


def test_warnings_show_on_the_answer_card_itself():
    card = answer_card(run(advice=advice(confident=False), numbers={"result": "fail", "detail": "x"}))
    assert "Not confident" in card and "Agent 1 reported different numbers than the tool" in card


def test_clean_answer_card_has_no_warnings_and_uses_agent2_why():
    card = answer_card(run())
    assert "Not confident" not in card and "different numbers" not in card
    assert "Agent 2&#x27;s own words." in card


def test_xray_is_an_accessible_native_toggle_in_both_states():
    page = today_html(run(), "cloudy", {"name": "Redmond, WA", "zip": "98052"}, "Cloudy")
    assert page.count("<details") == 2 and page.count("<summary") == 2
    assert '<details class="xr-details" open>' in page and '<details class="xr-details">' in page
    assert "X-ray this answer" in page and "Close X-ray" in page
    assert "<script" not in page and "<iframe" not in page
