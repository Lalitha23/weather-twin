"""Today tab: the live agent, behind a simple shared password (not auth).

Nothing calls a model until the password is entered. One live run is cached
for 30 minutes. Failures raise TodayError so they are never cached, and the
page only ever shows a friendly message.
"""
import hmac
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from agents.advisor import run_advisor
from agents.summarizer import make_client, run_summarizer
from app.report_data import differing_fields, load_active
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


DETAIL_MAX = 240
# Things that look like credentials: bearer tokens, sk-/key-/token- style IDs,
# and any long unbroken run of key-like characters.
SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)\S+"),
    re.compile(r"(?i)\b(?:sk|key|token|api)[-_][A-Za-z0-9_\-]{6,}"),
    re.compile(r"[A-Za-z0-9_\-]{32,}"),
]


class TodayError(Exception):
    """A failure with a friendly message, plus a short detail for the Details expander."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


def safe_detail(text: str) -> str:
    """One short line: first line only, secrets redacted, no stack trace."""
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    for env in ("NEBIUS_API_KEY", "APP_PASSWORD"):
        value = os.getenv(env, "")
        if value:
            line = line.replace(value, "[redacted]")
    for pattern in SECRET_PATTERNS:
        line = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "[redacted]", line)
    return line if len(line) <= DETAIL_MAX else line[:DETAIL_MAX - 1] + "…"


API_MESSAGE = re.compile(r"""['"]message['"]\s*:\s*(['"])(.*?)(?<!\\)\1""", re.DOTALL)
STATUS_CODE = re.compile(r"Error code: (\d{3})")


def error_detail(stage: str, error: str) -> str:
    """'api_error: AuthenticationError: Error code: 401 - {...'message': 'x'...}'
    -> 'Agent 1 · AuthenticationError (401): x'. Other errors pass through."""
    text = error.removeprefix("api_error: ")
    head = re.match(r"(\w+): (.*)", text, re.DOTALL)
    if head:
        kind, rest = head.groups()
        message = API_MESSAGE.search(rest)
        code = STATUS_CODE.search(rest)
        if message:
            status = f" ({code.group(1)})" if code else ""
            text = f"{kind}{status}: {message.group(2)}"
    return safe_detail(f"{stage} · {text}")


def _friendly(error: str) -> str:
    return MSG_MODEL if error.startswith("api_error") else MSG_SHAPE


@st.cache_data(ttl=CACHE_S, show_spinner=False)
def run_today(model_alias: str, prompt_version: str) -> dict:
    model = os.getenv(ALIASES.get(model_alias, ""), "") if model_alias in ALIASES else model_alias
    if not model:
        raise TodayError(MSG_SETUP, f"Setup · no model ID for {model_alias!r}")
    client = make_client()
    summarizer = run_summarizer(model, client, prompt_version)
    tool = summarizer.get("tool_output")
    if isinstance(tool, dict) and "error" in tool:
        raise TodayError(MSG_WEATHER, error_detail("Weather tool", str(tool["error"])))
    if summarizer["error"]:
        raise TodayError(_friendly(summarizer["error"]), error_detail("Agent 1", summarizer["error"]))
    advisor = run_advisor(model, summarizer["summary"], client, prompt_version)
    if advisor["error"]:
        raise TodayError(_friendly(advisor["error"]), error_detail("Agent 2", advisor["error"]))
    record = {"summarizer": summarizer, "advisor": advisor}
    return {
        "model": model,
        "prompt_version": prompt_version,
        "agent1": {"model": summarizer["model"], "prompt_version": summarizer["prompt_version"]},
        "agent2": {"model": advisor["model"], "prompt_version": advisor["prompt_version"]},
        "tool": tool,
        "summary": summarizer["summary"],
        "advice": advisor["advice"],
        "numbers": numbers_match_tool(record, {}),
        "tokens": summarizer["usage"]["total_tokens"] + advisor["usage"]["total_tokens"],
        "latency_s": (summarizer["latency_s"] or 0) + (advisor["latency_s"] or 0),
        "fetched_at": time.time(),
    }


LOCK_TEXT_TODAY = ("Today runs the live agent on Nebius Token Factory. "
                   "The password keeps strangers from spending your credits.")


def lock_card(key: str, text: str = LOCK_TEXT_TODAY) -> None:
    """The shared password card. One unlock covers Today and the live comparison."""
    password = os.getenv("APP_PASSWORD", "")
    with st.container(key=f"lockcard_{key}"):
        md('<h3 style="margin:0 0 6px;font-size:18px;">Enter your password</h3>'
           f'<p class="muted" style="margin:0 0 12px;">{esc(text)}</p>')
        with st.form(f"unlock_{key}", border=False):
            entered = st.text_input("Password", type="password", label_visibility="collapsed",
                                    placeholder="Password")
            if st.form_submit_button("Unlock", type="primary", use_container_width=True):
                # No APP_PASSWORD set means nothing unlocks: the page fails closed.
                if password and hmac.compare_digest(entered.encode(), password.encode()):
                    st.session_state["unlocked"] = True
                    st.rerun()
                st.error("That password didn't work.")


def _locked() -> None:
    lock_card("today")
    md('<p class="muted" style="text-align:center;margin-top:12px;font-size:14px;">'
       'Test Lab stays open to everyone. It only shows saved results.</p>')


def display_conditions(text: str | None) -> str:
    if not text:
        return ""
    return DISPLAY_CONDITIONS.get(text.lower(), text[0].upper() + text[1:])


def _fmt(value, unit: str) -> str:
    return "–" if value is None else f"{value:g}{unit}"


def _weather_card(r: dict) -> str:
    """The raw numbers from the tool."""
    tool = r["tool"]
    observed = (tool.get("observed_at") or "")[:16]
    try:
        day = datetime.fromisoformat(observed).strftime("%a %b %-d")
    except ValueError:
        day = "Today"
    temp = "–" if tool.get("temperature_c") is None else f"{round(tool['temperature_c'])}°"
    loc = load_location()
    return f"""<div class="card flow-card">
  <div class="label">Weather data · get_weather</div>
  <div class="place">{esc(loc['name'])} {esc(loc['zip'])}</div>
  <div class="weather-top"><span>{esc(day)} · {esc(tool.get('time_of_day') or '')}</span>
    <span class="cond">{esc(display_conditions(tool.get('conditions')))}</span></div>
  <div class="weather-main"><div class="temp">{temp}<span style="font-size:22px;">C</span></div>
    <div class="wx-side">Rain {_fmt(tool.get('rain_chance_pct'), '%')}<br>Wind {_fmt(tool.get('wind_kph'), ' km/h')}</div></div>
</div>"""


def _agent_pills(agent: dict) -> str:
    return (f'<div class="pills" style="margin:0 0 12px;"><span class="pill">{esc(agent["model"].split("/")[-1])}</span>'
            f'<span class="pill">prompt {esc(agent["prompt_version"])}</span></div>')


def _agent1_card(r: dict) -> str:
    note = ""
    if r["numbers"]["result"] == "fail":
        note = '<div class="note-orange">Agent 1 reported different numbers than the tool.</div>'
    summary = json_block(r["summary"], differing_fields(r["tool"], r["summary"]))
    return (f'<div class="card flow-card"><div class="ftitle">Agent 1, Summarizer</div>{_agent_pills(r["agent1"])}'
            f'{summary}{note}</div>')


def _handoff() -> str:
    return ('<div class="handoff" aria-label="handoff"><div class="arrow"></div>'
            '<div class="handoff-label">handoff</div>'
            '<div class="handoff-sub">Agent 2 reads only this summary</div></div>')


def _tile(name: str, yes: bool) -> str:
    return (f'<div class="tile {"yes" if yes else ""}"><div class="label">{name}</div>'
            f'<div class="big">{"Yes" if yes else "No"}</div></div>')


def _agent2_card(r: dict) -> str:
    a = r["advice"]
    confidence = ('<span class="pill conf-yes">Confident</span>' if a["confident"]
                  else '<span class="pill conf-no">Not confident</span>')
    return (f'<div class="card flow-card"><div class="ftitle">Agent 2, Advisor</div>{_agent_pills(r["agent2"])}'
            f'<div class="tiles">{_tile("Jacket", a["jacket"])}{_tile("Umbrella", a["umbrella"])}</div>'
            f'<div style="margin:0 0 10px;">{confidence}</div>'
            f'<div class="label">Why</div><div style="font-size:15px;">{esc(a["why"])}</div></div>')


def _unlocked() -> None:
    active = load_active()
    try:
        with st.spinner("Checking today's weather…"):
            r = run_today(active["model"], active["prompt_version"])
    except TodayError as e:
        _error(str(e), e.detail)
        return
    except Exception as e:  # never show a stack trace
        _error("Something went wrong. Try Refresh in a minute.",
               safe_detail(f"{type(e).__name__}: {e}"))
        return

    md(f'<div class="flow">{_weather_card(r)}{_agent1_card(r)}{_handoff()}{_agent2_card(r)}</div>')
    updated = datetime.fromtimestamp(r["fetched_at"], PACIFIC).strftime("%H:%M")
    with st.container(key="footer_line"):
        md(f'<p class="muted mono" style="margin:0 0 8px;font-size:13px;">{r["tokens"]:,} tokens · '
           f'{r["latency_s"]:.1f} s · Cached · updated {updated}</p>')
        _refresh_button()


def _error(message: str, detail: str) -> None:
    """Friendly card, then a collapsed Details line. Only reached after unlock."""
    md(f'<div class="card err">{esc(message)}</div>')
    if detail:
        with st.expander("Details", expanded=False):
            md(f'<p class="mono" style="margin:0;font-size:13px;word-break:break-word;">{esc(detail)}</p>')
    _refresh_button()


def _refresh_button() -> None:
    if st.button("Refresh", use_container_width=True):
        run_today.clear()
        st.rerun()


def render() -> None:
    if st.session_state.get("unlocked"):
        with st.container(key="today_flow"):
            _unlocked()
    else:
        with st.container(key="today"):
            _locked()
