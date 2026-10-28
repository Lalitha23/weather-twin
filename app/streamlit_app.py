"""Weather Twin app: Today (live agent) and Test Lab (saved results).

Run from the repo root:  streamlit run app/streamlit_app.py
Layout, colours and wording follow docs/DESIGN.md, and docs/REDESIGN.md where they differ.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402


def load_secrets() -> None:
    """.env locally, st.secrets when deployed. Existing env vars win."""
    load_dotenv(ROOT / ".env")
    try:
        for key, value in st.secrets.items():
            # Empty values are skipped so a half-filled secrets file keeps the defaults.
            if isinstance(value, (str, int, float, bool)) and str(value) != "":
                os.environ.setdefault(key, str(value))
    except Exception:  # no secrets file locally
        pass
    # Today uses live weather by default. The live comparison passes backend
    # and scenario to the tool directly, so the two never share this setting.
    os.environ["WEATHER_BACKEND"] = "live"


st.set_page_config(page_title="Weather Twin", page_icon="☂", layout="wide")
load_secrets()

from app import lab, report, today  # noqa: E402
from app.ui import esc, inject_css, md, title  # noqa: E402

INTRO = ("My son doesn't check the weather before school, so I'm building two agents to tell him: "
         "Agent 1 reads the weather, Agent 2 decides jacket and umbrella and, later, will tell him by text or a speaker in his room. "
         "Before anything texts a child, Test Lab runs both agents against a twin of the weather tool, "
         "feeds them bad and malicious data on purpose, and checks whether a failure in Agent 1 travels to Agent 2.")

inject_css()
with st.container(key="wt_header"):
    title()
    md(f'<p class="muted" style="margin:0 0 4px;max-width:880px;">{esc(INTRO)}</p>'
       '<p style="margin:0;"><b>New here? Open Test Lab → Official report to see what I found.</b></p>')
tab_today, tab_lab = st.tabs(["Today", "Test Lab"])
# Test Lab first in code, so a slow Today run can't leave the report blank.
with tab_lab:
    official, live = st.tabs(["Official report", ":material/lock: Live comparison"])
    with official:
        report.render()
    with live:
        lab.render()
with tab_today:
    today.render()
