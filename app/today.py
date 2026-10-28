"""Today tab: the live agent, run once a day and shown to everyone.

The first visit of each Pacific day runs the agents; everyone after that sees
the cached run. Refresh is behind a simple shared password (not auth), so
visitors can't spend credits. Failures raise TodayError so they are never
cached, and the page only ever shows a friendly message.
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
from app.report_data import load_active
from app.sky import preview_mood, sky_mood
from app.ui import esc, md
from app.xray import error_html, today_html
from checks.checks import numbers_match_tool
from tools.weather_live import load_location

ALIASES = {"nemotron": "NEMOTRON_MODEL", "compare": "COMPARE_MODEL"}
PACIFIC = ZoneInfo("America/Los_Angeles")
# One run per Pacific day: the date is part of the cache key, the TTL is a backstop.
CACHE_S = 26 * 60 * 60
CACHE_NOTE = ("This is a cached run. Today runs the agents once a day and saves the result, "
              "so the page stays open to everyone without the credits being misused. "
              "Refresh is password protected.")

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

MSG_WEATHER = "Couldn't reach the weather service. Try again in a minute."
MSG_MODEL = "Couldn't reach the model on Token Factory. Try again in a minute."
MSG_SHAPE = "The agent's answer came back in the wrong shape. Try again in a minute."
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


def pacific_day() -> str:
    return datetime.now(PACIFIC).date().isoformat()


@st.cache_data(ttl=CACHE_S, max_entries=4, show_spinner=False)
def run_today(model_alias: str, prompt_version: str, day: str) -> dict:
    """day is only the cache key, so a new Pacific day starts a new run."""
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


LOCK_TEXT_TODAY = ("Refresh runs the live agent again on Nebius Token Factory. "
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


def _refresh_lock() -> None:
    with st.expander(":material/lock: Refresh (password)", expanded=False):
        lock_card("today")


def display_conditions(text: str | None) -> str:
    if not text:
        return ""
    return DISPLAY_CONDITIONS.get(text.lower(), text[0].upper() + text[1:])


def _mood(r: dict | None) -> str:
    """The sky for this run. ?sky=<mood> previews another sky; it never changes the data."""
    preview = preview_mood(st.query_params.get("sky"))
    if preview:
        return preview
    tool = r["tool"] if r and isinstance(r.get("tool"), dict) else {}
    return sky_mood(tool.get("conditions"), tool.get("time_of_day"))


def _today() -> None:
    active = load_active()
    try:
        with st.spinner("Checking today's weather…"):
            r = run_today(active["model"], active["prompt_version"], pacific_day())
    except TodayError as e:
        _error(str(e), e.detail)
        return
    except Exception as e:  # never show a stack trace
        _error("Something went wrong. Try again in a minute.",
               safe_detail(f"{type(e).__name__}: {e}"))
        return

    st.html(today_html(r, _mood(r), load_location(), display_conditions(r["tool"].get("conditions"))))
    updated = datetime.fromtimestamp(r["fetched_at"], PACIFIC).strftime("%a %b %-d, %H:%M PT")
    with st.container(key="footer_line"):
        md(f'<p class="muted mono" style="margin:0 0 8px;font-size:13px;">{esc(r["agent2"]["model"].split("/")[-1])} · '
           f'prompt {esc(r["agent2"]["prompt_version"])} · {r["tokens"]:,} tokens · '
           f'{r["latency_s"]:.1f} s · Cached run · updated {updated}</p>'
           f'<p class="muted" style="margin:0 0 8px;font-size:13px;">{esc(CACHE_NOTE)}</p>')
        _refresh_button()


def _error(message: str, detail: str) -> None:
    """Friendly card, then a collapsed Details line."""
    st.html(error_html(message))
    if detail:
        with st.expander("Details", expanded=False):
            md(f'<p class="mono" style="margin:0;font-size:13px;word-break:break-word;">{esc(detail)}</p>')
    _refresh_button()


def _refresh_button() -> None:
    """Refresh clears the shared cache and spends credits, so it needs the password."""
    if not st.session_state.get("unlocked"):
        _refresh_lock()
        return
    if st.button("Refresh", use_container_width=True):
        run_today.clear()
        st.rerun()


def render() -> None:
    with st.container(key="today_flow"):
        _today()
