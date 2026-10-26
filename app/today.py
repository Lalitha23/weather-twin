"""Today tab: the live agent, behind a simple shared password (not auth).

Nothing calls a model until the password is entered. One live run is cached
for 30 minutes. Failures raise TodayError so they are never cached, and the
page only ever shows a friendly message.
"""
import hmac
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from agents.advisor import run_advisor
from agents.summarizer import make_client, run_summarizer
from app.report_data import load_active
from app.ui import esc, json_block, md
from checks.checks import numbers_match_tool
from tools.weather_live import load_location

ALIASES = {"nemotron": "NEMOTRON_MODEL", "compare": "COMPARE_MODEL"}
PACIFIC = ZoneInfo("America/Los_Angeles")
CACHE_S = 30 * 60

# Friendlier words for the Today card only. The tool's conditions text is unchanged.
DISPLAY_CONDITIONS = {
    "clear sky": "Clear",
    "mainly clear": "Mostly clear",
    "overcast": "Cloudy",
    "fog": "Foggy",
    "freezing fog": "Icy fog",
    "drizzle": "Drizzle",
    "light freezing drizzle": "Light icy drizzle",
    "freezing drizzle": "Icy drizzle",
    "light freezing rain": "Light icy rain",
    "freezing rain": "Icy rain",
    "snow grains": "Light snow",
    "light showers": "Light showers",
    "thunderstorm with hail": "Thunderstorm, hail",
    "thunderstorm with heavy hail": "Thunderstorm, heavy hail",
}

MSG_WEATHER = "Couldn't reach the weather service. Try Refresh in a minute."
MSG_MODEL = "Couldn't reach the model on Token Factory. Try Refresh in a minute."
MSG_SHAPE = "The agent's answer came back in the wrong shape. Try Refresh."
MSG_SETUP = "Today isn't set up yet. The model setting is missing."


class TodayError(Exception):
    """A failure with a message that is safe to show."""


def _friendly(error: str) -> str:
    return MSG_MODEL if error.startswith("api_error") else MSG_SHAPE


@st.cache_data(ttl=CACHE_S, show_spinner=False)
def run_today(model_alias: str, prompt_version: str) -> dict:
    model = os.getenv(ALIASES.get(model_alias, ""), "") if model_alias in ALIASES else model_alias
    if not model:
        raise TodayError(MSG_SETUP)
    client = make_client()
    summarizer = run_summarizer(model, client, prompt_version)
    tool = summarizer.get("tool_output")
    if isinstance(tool, dict) and "error" in tool:
        raise TodayError(MSG_WEATHER)
    if summarizer["error"]:
        raise TodayError(_friendly(summarizer["error"]))
    advisor = run_advisor(model, summarizer["summary"], client, prompt_version)
    if advisor["error"]:
        raise TodayError(_friendly(advisor["error"]))
    record = {"summarizer": summarizer, "advisor": advisor}
    return {
        "model": model,
        "prompt_version": prompt_version,
        "tool": tool,
        "summary": summarizer["summary"],
        "advice": advisor["advice"],
        "numbers": numbers_match_tool(record, {}),
        "tokens": summarizer["usage"]["total_tokens"] + advisor["usage"]["total_tokens"],
        "latency_s": (summarizer["latency_s"] or 0) + (advisor["latency_s"] or 0),
        "fetched_at": time.time(),
    }


def _locked() -> None:
    password = os.getenv("APP_PASSWORD", "")
    with st.container(key="lockcard"):
        md('<h3 style="margin:0 0 6px;font-size:18px;">Enter your password</h3>'
           '<p class="muted" style="margin:0 0 12px;">Today runs the live agent on Nebius Token Factory. '
           'The password keeps strangers from spending your credits.</p>')
        if not password:
            md(f'<div class="note-orange">Today isn\'t set up yet. APP_PASSWORD is missing.</div>')
            return
        with st.form("unlock", border=False):
            entered = st.text_input("Password", type="password", label_visibility="collapsed",
                                    placeholder="Password")
            if st.form_submit_button("Unlock", type="primary", use_container_width=True):
                if hmac.compare_digest(entered.encode(), password.encode()):
                    st.session_state["unlocked"] = True
                    st.rerun()
                st.error("That password didn't work.")
    md('<p class="muted" style="text-align:center;margin-top:12px;font-size:14px;">'
       'Test Lab stays open to everyone. It only shows saved results.</p>')


def display_conditions(text: str | None) -> str:
    if not text:
        return ""
    return DISPLAY_CONDITIONS.get(text.lower(), text[0].upper() + text[1:])


def _fmt(value, unit: str) -> str:
    return "–" if value is None else f"{value:g}{unit}"


def _weather_card(r: dict) -> None:
    tool = r["tool"]
    observed = (tool.get("observed_at") or "")[:16]
    try:
        day = datetime.fromisoformat(observed).strftime("%a %b %-d")
    except ValueError:
        day = "Today"
    note = ""
    if r["numbers"]["result"] == "fail":
        note = '<div class="note-orange">Agent 1 reported different numbers. See Agent 1 summary.</div>'
    temp = "–" if tool.get("temperature_c") is None else f"{round(tool['temperature_c'])}°"
    loc = load_location()
    md(f"""<div class="card">
  <div class="place">{esc(loc['name'])} {esc(loc['zip'])}</div>
  <div class="weather-top"><span>{esc(day)} · {esc(tool.get('time_of_day') or '')}</span>
    <span class="cond">{esc(display_conditions(tool.get('conditions')))}</span></div>
  <div class="weather-main"><div class="temp">{temp}<span style="font-size:24px;">C</span></div>
    <div class="wx-side">Rain {_fmt(tool.get('rain_chance_pct'), '%')}<br>Wind {_fmt(tool.get('wind_kph'), ' km/h')}</div></div>
  {note}
</div>""")


def _tile(name: str, yes: bool) -> str:
    return (f'<div class="tile {"yes" if yes else ""}"><div class="label">{name}</div>'
            f'<div class="big">{"Yes" if yes else "No"}</div></div>')


def _unlocked() -> None:
    active = load_active()
    try:
        with st.spinner("Checking today's weather…"):
            r = run_today(active["model"], active["prompt_version"])
    except TodayError as e:
        md(f'<div class="card err">{esc(e)}</div>')
        _refresh_button()
        return
    except Exception:  # never show a stack trace
        md('<div class="card err">Something went wrong. Try Refresh in a minute.</div>')
        _refresh_button()
        return

    a = r["advice"]
    _weather_card(r)
    md(f'<div class="tiles">{_tile("Jacket", a["jacket"])}{_tile("Umbrella", a["umbrella"])}</div>')
    md(f'<div class="card"><div class="label">Why</div><div style="font-size:16px;">{esc(a["why"])}</div></div>')
    with st.expander("Agent 1 summary"):
        md(json_block(r["summary"]))
    updated = datetime.fromtimestamp(r["fetched_at"], PACIFIC).strftime("%H:%M")
    with st.container(key="footer"):
        md(f'<div class="pills"><span class="pill">{esc(r["model"].split("/")[-1])}</span>'
           f'<span class="pill">prompt {esc(r["prompt_version"])}</span>'
           f'<span class="pill">{r["tokens"]:,} tokens · {r["latency_s"]:.1f} s</span></div>'
           f'<p class="muted" style="margin:12px 0 8px;font-size:14px;">Cached · updated {updated}</p>')
        _refresh_button()


def _refresh_button() -> None:
    if st.button("Refresh", use_container_width=True):
        run_today.clear()
        st.rerun()


def render() -> None:
    with st.container(key="today"):
        if st.session_state.get("unlocked"):
            _unlocked()
        else:
            _locked()
