"""Run the app locally with Today showing a saved official run. No model calls.

    streamlit run scripts/preview_today.py

Pick the run with query parameters, for example
    http://localhost:8501/?run=missing_field
    http://localhost:8501/?run=clear_day&sky=rain
`run` is an official scenario (Nemotron v2, repeat 1). `sky` only changes the background.
`xray=open` or `xray=closed` forces the X-ray state at every width, for screenshots.
For screenshots and design work only. The deployed app never imports this file.
"""
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app import today, xray  # noqa: E402
from checks.checks import numbers_match_tool  # noqa: E402

RUNS_FILE = ROOT / "results" / "official_matrix_oct25.jsonl"
MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


def saved_today(scenario: str, prompt_version: str = "v2") -> dict:
    """An official run reshaped into what today.run_today returns."""
    for line in RUNS_FILE.read_text().splitlines():
        r = json.loads(line)
        if (r["scenario"], r["model"], r["prompt_version"], r["repeat"]) == (scenario, MODEL, prompt_version, 1):
            s, a = r["summarizer"], r["advisor"]
            return {
                "model": MODEL, "prompt_version": prompt_version,
                "agent1": {"model": s["model"], "prompt_version": s["prompt_version"]},
                "agent2": {"model": a["model"], "prompt_version": a["prompt_version"]},
                "tool": s["tool_output"], "summary": s["summary"], "advice": a["advice"],
                "numbers": numbers_match_tool({"summarizer": s}, {}),
                "tokens": s["usage"]["total_tokens"] + a["usage"]["total_tokens"],
                "latency_s": (s["latency_s"] or 0) + (a["latency_s"] or 0),
                "fetched_at": 1793030700.0,  # a fixed time, so screenshots don't change
            }
    raise SystemExit(f"No official run for {scenario!r}")


scenario = st.query_params.get("run", "clear_day")
today.run_today = lambda *_args: saved_today(scenario)

# Streamlit keeps modules between reruns, so remember the real function once.
real_xray = xray._preview_original = getattr(xray, "_preview_original", xray.xray_html)
forced = st.query_params.get("xray")
if forced in ("open", "closed"):
    xray.xray_html = lambda r, layout, open_=None, **kw: real_xray(r, layout, forced == "open", **kw)
else:
    xray.xray_html = real_xray
runpy.run_path(str(ROOT / "app" / "streamlit_app.py"), run_name="__main__")
