"""Shared CSS and small HTML helpers, following docs/DESIGN.md."""
import html
import json
from typing import Any

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root {
  --ground:#F4F5F7; --surface:#FFFFFF; --ink:#15181D; --muted:#5B6470; --line:#E1E4E9;
  --blue:#1D5FBF; --pass-bg:#E3ECFA; --pass-fg:#16498F; --part-bg:#FFF3DC; --part-fg:#6B4400;
  --hard:#B5530E; --soft-bg:#FCEBDD; --soft-fg:#7A3507;
  --mono:'IBM Plex Mono', ui-monospace, monospace; --sans:'IBM Plex Sans', system-ui, sans-serif;
  --pad:24px;
}
html, body, [data-testid="stAppViewContainer"], .stMarkdown, button, input, label { font-family: var(--sans); }
[data-testid="stAppViewContainer"] { background: var(--ground); }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1200px; padding-top: 1.5rem; }
[data-testid="stHeader"] { background: transparent; }
* { min-width: 0; }
.stMarkdown p, .stMarkdown li { font-size: 15px; }
.mono { font-family: var(--mono); }
.muted { color: var(--muted); }

/* Title */
.wt-title { display:flex; align-items:center; gap:10px; font-weight:700; font-size:22px; color:var(--ink); margin:0 0 4px; }
.wt-mark { position:relative; width:26px; height:18px; flex:none; }
.wt-mark span { position:absolute; top:0; width:18px; height:18px; border-radius:50%; border:2px solid var(--blue); }
.wt-mark span:first-child { left:0; } .wt-mark span:last-child { left:8px; background:rgba(29,95,191,.15); }

/* Tabs */
.stTabs [data-baseweb="tab"] { font-size:16px; min-height:44px; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--blue); }

/* Cards */
.card { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:var(--pad); margin:0 0 16px; color:var(--ink); }
.card h3 { margin:0 0 6px; font-size:18px; font-weight:600; }
.label { font-size:13px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
.st-key-lockcard, .st-key-footer { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:var(--pad); }
.st-key-today { max-width:480px; margin:0 auto; width:100%; }

/* Today */
.weather-top { display:flex; justify-content:space-between; gap:12px; font-size:14px; color:var(--muted); }
.weather-main { display:flex; justify-content:space-between; align-items:flex-end; gap:12px; margin-top:8px; }
.temp { font-family:var(--mono); font-size:64px; line-height:1; font-weight:500; letter-spacing:-.02em; }
.wx-side { font-family:var(--mono); font-size:15px; text-align:right; line-height:1.6; }
.cond { font-weight:600; color:var(--ink); text-align:right; }
.note-orange { margin-top:14px; background:var(--soft-bg); color:var(--soft-fg); border-radius:10px; padding:8px 12px; font-size:14px; }
.tiles { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:0 0 16px; }
.tile { border-radius:18px; padding:20px; border:1px solid var(--line); background:var(--surface); color:var(--ink); }
.tile.yes { background:var(--blue); border-color:var(--blue); color:#fff; }
.tile .label { color:inherit; opacity:.8; }
.tile .big { font-size:40px; font-weight:700; line-height:1.1; }
.pills { display:flex; flex-wrap:wrap; gap:8px; }
.pill { font-family:var(--mono); font-size:13px; border:1px solid var(--line); border-radius:999px; padding:4px 10px; background:var(--ground); color:var(--ink); }
.err { background:var(--soft-bg); border:1px solid #F3C9A7; color:var(--soft-fg); }

/* Decision */
.decision { background:var(--ink); color:#fff; border-radius:18px; padding:var(--pad); margin:0 0 16px;
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.3fr); gap:24px; }
.decision .label { color:#AEB6C2; }
.decision h2 { font-size:28px; margin:0 0 8px; color:#fff; font-weight:700; line-height:1.2; }
.decision .cost { color:#C9CFD8; font-size:15px; }
.reasons { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; }
.reason { background:#22272F; border:1px solid #333A45; border-radius:14px; padding:14px; }
.reason b { display:block; font-size:16px; margin-bottom:4px; }
.reason span { color:#AEB6C2; font-size:13px; }
.btn-disabled { margin-top:16px; display:inline-block; min-height:44px; line-height:44px; padding:0 16px; border-radius:10px;
  border:1px solid #3A414C; color:#8A93A0; font-size:14px; cursor:not-allowed; }

/* Results table */
.legend { display:flex; flex-wrap:wrap; gap:14px; font-size:13px; color:var(--muted); margin:4px 0 12px; }
.legend i { display:inline-block; width:14px; height:14px; border-radius:4px; vertical-align:-2px; margin-right:6px; }
.scroll { overflow-x:auto; -webkit-overflow-scrolling:touch; }
table.results { border-collapse:separate; border-spacing:6px; width:100%; min-width:720px; }
table.results th, table.results td { border:none; }
table.results th { font-size:14px; font-weight:600; text-align:center; padding:6px; color:var(--ink); }
table.results th:first-child { text-align:left; }
table.results td.name { font-family:var(--mono); font-size:14px; padding:6px 8px 6px 0; vertical-align:top; }
table.results td.name div { font-family:var(--sans); color:var(--muted); font-size:13px; }
.c { font-family:var(--mono); font-size:14px; text-align:center; border-radius:8px; padding:10px 6px; white-space:nowrap; }
.c.pass { background:var(--pass-bg); color:var(--pass-fg); }
.c.partial { background:var(--part-bg); color:var(--part-fg); }
.c.hard { background:var(--hard); color:#fff; }
.c.na { color:var(--muted); }
.c.misleading { outline:2px dashed var(--hard); outline-offset:-2px; }
.c small { display:block; font-family:var(--sans); font-size:13px; color:var(--hard); white-space:normal; }
.badge { display:inline-block; background:var(--blue); color:#fff; font-size:13px; border-radius:999px; padding:1px 8px; margin-left:6px; font-weight:500; }

/* Run trace */
.callout { background:var(--surface); border-left:4px solid var(--hard); border-radius:10px; padding:12px 16px; margin:8px 0 16px; font-size:15px; }
.panel { background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:16px; height:100%; }
.panel.start { border:2px solid var(--hard); }
.panel .ph { margin:0 0 8px; font-size:15px; font-weight:600; display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap; }
.panel .ph em { font-style:normal; font-size:13px; color:var(--hard); font-weight:600; }
.json { font-family:var(--mono); font-size:13px; word-break:break-word; line-height:1.55; color:var(--ink); }
.json .kv { padding-left:16px; }
.json .hl { background:var(--soft-bg); color:var(--soft-fg); border-radius:4px; font-weight:600; }
.checks { display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:10px; margin-top:12px; }
.chk { border-radius:12px; padding:10px 12px; border:1px solid var(--line); background:var(--surface); font-size:13px; }
.chk b { font-family:var(--mono); font-size:13px; }
.chk.fail { background:var(--soft-bg); border-color:#F3C9A7; color:var(--soft-fg); }
.chk .r { float:right; font-weight:600; }
.chk p { margin:4px 0 0; color:inherit; opacity:.85; word-break:break-word; }

table.plain { border-collapse:collapse; width:100%; font-size:14px; }
table.plain th, table.plain td { text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); }
table.plain td.n { font-family:var(--mono); text-align:right; }
table.plain th.n { text-align:right; }
.foot { font-size:13px; color:var(--muted); margin-top:10px; }

/* Buttons and inputs: 44 px touch targets */
.stButton button, .stFormSubmitButton button { min-height:44px; border-radius:10px; }
.stTextInput input { min-height:44px; }
[data-testid="stSelectbox"] div[data-baseweb="select"] > div { min-height:44px; }

@media (max-width: 640px) {
  :root { --pad:16px; }
  [data-testid="stMainBlockContainer"], .block-container { padding-left:16px; padding-right:16px; }
  .decision { grid-template-columns:1fr; }
  .reasons { grid-template-columns:1fr; }
  .decision h2 { font-size:24px; }
  .temp { font-size:56px; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(value: Any) -> str:
    return html.escape(str(value))


def md(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def title() -> None:
    md('<div class="wt-title"><div class="wt-mark"><span></span><span></span></div>Weather Twin</div>')


def json_block(data: Any, highlight: set[str] = frozenset()) -> str:
    """Flat JSON as HTML, one key per line, highlighted keys marked.

    Built from divs, not <pre>, because st.markdown collapses newlines.
    """
    if not isinstance(data, dict):
        return f'<div class="json"><div>{esc(json.dumps(data, ensure_ascii=False))}</div></div>'
    rows = []
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        text = f'"{esc(key)}": {esc(json.dumps(value, ensure_ascii=False))}{comma}'
        cls = "kv hl" if key in highlight else "kv"
        rows.append(f'<div class="{cls}">{text}</div>')
    return f'<div class="json"><div>{{</div>{"".join(rows)}<div>}}</div></div>'
