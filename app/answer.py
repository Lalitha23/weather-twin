"""Words for Today's answer card. Pure functions, no Streamlit, no model calls.

rules_badge is display logic only. It mirrors checks.umbrella_rule and
checks.jacket_rule (umbrella over 50% rain, jacket under 10 °C), applied to the
weather tool's numbers. It does not change or replace checks/checks.py.
"""
from datetime import datetime

RAIN_LIMIT_PCT = 50
COLD_LIMIT_C = 10

MATCH = "✓ matches the weather data"
MISMATCH = "✗ doesn't match the weather data"
UNKNOWN = "Rules can't be checked, weather data incomplete"


def answer_lines(advice: dict) -> tuple[str, str]:
    return ("Take a jacket." if advice["jacket"] else "No jacket.",
            "Take an umbrella." if advice["umbrella"] else "No umbrella.")


def rules_badge(tool: dict | None, advice: dict | None) -> dict:
    """Compare Agent 2's decision with the rules applied to the tool's numbers.

    Returns {"state": "match" | "mismatch" | "unknown", "text": str, "why": [str]}.
    """
    tool = tool if isinstance(tool, dict) and "error" not in tool else {}
    temp, rain = tool.get("temperature_c"), tool.get("rain_chance_pct")
    if advice is None or temp is None or rain is None:
        return {"state": "unknown", "text": UNKNOWN, "why": []}
    want_umbrella, want_jacket = rain > RAIN_LIMIT_PCT, temp < COLD_LIMIT_C
    why = []
    if advice["umbrella"] != want_umbrella:
        why.append(f"rain {rain:g}% {'is over' if want_umbrella else 'is not over'} {RAIN_LIMIT_PCT}%, "
                   f"so {'umbrella' if want_umbrella else 'no umbrella'}")
    if advice["jacket"] != want_jacket:
        why.append(f"{temp:g} °C {'is under' if want_jacket else 'is not under'} {COLD_LIMIT_C} °C, "
                   f"so {'jacket' if want_jacket else 'no jacket'}")
    if why:
        return {"state": "mismatch", "text": MISMATCH, "why": why}
    return {"state": "match", "text": MATCH, "why": []}


def weather_time(observed_at: str | None) -> str | None:
    """"Mon · weather at 11:23" from the tool's observed_at, or None if it doesn't parse."""
    try:
        when = datetime.fromisoformat((observed_at or "")[:16])
    except ValueError:
        return None
    return f"{when:%a} · weather at {when:%H:%M}"
