"""Shared CSS and small HTML helpers, following docs/REDESIGN.md (sky wash tokens, Geist)."""
import html
import json
from typing import Any

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800;900&family=Geist+Mono:wght@400;500;600&display=swap');
:root {
  --ground:#F6F9FC; --surface:#FFFFFF; --ink:#0F1B2A; --muted:#5B6B7D; --line:#D3E2F0; --inner:#E3EBF3;
  --blue:#0B5CAD; --pass-bg:#EEF5FC; --pass-bd:#BFD6EE; --pass-fg:#0B5CAD; --part-bg:#FFF7E6; --part-fg:#7A4B00;
  --hard:#C2410C; --orange:#EA580C; --soft-bg:#FFF4EC; --soft-bd:#FDBA8C; --soft-fg:#C2410C;
  --shadow:0 8px 24px rgba(11,92,173,.08);
  --mono:'Geist Mono', ui-monospace, monospace; --sans:'Geist', system-ui, sans-serif;
  --pad:24px;
}
html, body, [data-testid="stAppViewContainer"], .stMarkdown, button, input, label { font-family: var(--sans); }
/* Streamlit sets Source Sans directly on these, so name them; .mono keeps Geist Mono. */
.stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp li, .stApp button, .stApp input, .stApp label,
.stApp textarea, .stApp [data-baseweb="select"], .stApp [data-testid="stMarkdownContainer"] { font-family: var(--sans); }
.stApp .mono, .stApp code { font-family: var(--mono); }
/* Sky wash behind Test Lab, with two soft clouds drifting. Today paints its own live sky over this. */
[data-testid="stAppViewContainer"] { background: linear-gradient(180deg, #CFE5FA 0%, #E7F2FC 45%, #F7FBFE 100%); }
[data-testid="stAppViewContainer"]::before, [data-testid="stAppViewContainer"]::after {
  content:""; position:fixed; z-index:0; pointer-events:none; border-radius:80px; animation:wash-drift 16s ease-in-out infinite alternate; }
[data-testid="stAppViewContainer"]::before { width:420px; height:120px; top:70px; left:6%; background:rgba(255,255,255,.7); }
[data-testid="stAppViewContainer"]::after { width:340px; height:100px; top:150px; right:8%; background:rgba(255,255,255,.55); }
@keyframes wash-drift { to { transform:translateX(30px); } }
[data-testid="stMain"] { position:relative; z-index:1; }
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) [data-testid="stAppViewContainer"]::before,
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) [data-testid="stAppViewContainer"]::after { display:none; }
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
.card { background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:var(--pad); margin:0 0 16px; color:var(--ink); box-shadow:var(--shadow); }
.card h3 { margin:0 0 6px; font-size:18px; font-weight:600; }
.label { font-size:13px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
[class*="st-key-lockcard"], .st-key-footer, .st-key-setup, [class*="st-key-result_"] { background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:var(--pad); box-shadow:var(--shadow); }
.st-key-wt_header { background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); border-radius:20px; padding:16px 20px; }
.stTabs [role="tablist"] { background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); border-radius:999px; padding:0 14px; width:fit-content; }

/* Official report hero */
.hero { margin:8px 0 18px; }
.hero .kicker { font-family:var(--mono); font-size:13px; letter-spacing:.06em; color:var(--hard); font-weight:600; }
.hero h1 { font-size:50px; font-weight:900; line-height:1.05; letter-spacing:-.03em; margin:10px 0 12px; color:var(--ink); padding:0; }
.hero h1 .tail { color:var(--muted); }
.hero .lead { font-size:17px; margin:0 0 6px; color:var(--ink); }
.hero .small { font-size:13px; color:var(--muted); margin:0; }
.jump-label { font-family:var(--mono); font-size:13px; letter-spacing:.06em; color:var(--muted); margin:0 0 6px; text-transform:uppercase; }
.st-key-jumps .stButton button { background:var(--surface); border:1px solid var(--line); border-radius:999px; font-weight:600; }
.st-key-jumps .stButton button:hover { border-color:var(--blue); color:var(--blue); }
@media (max-width: 1023px) {
  .hero h1 { font-size:32px; margin:8px 0 10px; }
  .hero .lead { font-size:15px; }
  .st-key-jumps [data-testid="stHorizontalBlock"] { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:8px; }
  .st-key-jumps [data-testid="stColumn"] { width:auto !important; min-width:0; flex:none; }
  .st-key-jumps .stButton button { min-height:40px; padding:4px 12px; font-size:13px; line-height:1.2; }
  .st-key-jumps .stButton button .stMarkdownEllipsis, .st-key-jumps .stButton button p {
    white-space:normal; overflow:visible; text-overflow:clip; font-size:13px; line-height:1.2; }
}
.st-key-picker { background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:10px 16px 2px; box-shadow:var(--shadow); margin-top:4px; }

/* The Inspector iframe holds only the pipeline, the replay controls and the step panel.
   st.iframe(height="content") sizes it to that content. */

/* Inspector side panel, native beside the iframe */
.shipped { background:var(--ink); color:#fff; border-radius:20px; padding:20px; margin:0 0 12px; }
.shipped .kicker { font-family:var(--mono); font-size:13px; letter-spacing:.08em; color:#AEB6C2; }
.shipped .sname { font-size:20px; font-weight:800; margin:6px 0; }
.shipped p { margin:0; color:#C9D2DD; font-size:14px; }
.stats { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.stat { background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:16px; box-shadow:var(--shadow); color:var(--ink); }
.stat .kicker { font-family:var(--mono); font-size:13px; color:var(--muted); }
.stat b { display:block; font-size:30px; font-weight:800; margin:4px 0 2px; font-family:var(--mono); letter-spacing:-.02em; }
.stat span { font-size:13px; color:var(--muted); }
.st-key-footer_line .stButton button { width:auto; min-width:160px; }
@media (max-width: 900px) {
  .st-key-footer_line .stButton button { width:100%; }
}
.err { background:var(--soft-bg); border:1px solid #F3C9A7; color:var(--soft-fg); }

/* Decision */
.decision { background:var(--ink); color:#fff; border-radius:18px; padding:var(--pad); margin:0 0 16px;
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.3fr); gap:24px; }
.decision .label { color:#AEB6C2; }
.decision h2 { font-size:28px; margin:0 0 8px; color:#fff; font-weight:700; line-height:1.2; }
.decision .cost { color:#C9CFD8; font-size:15px; }
.reasons { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; }
.reason { background:#1B2A3B; border:1px solid #2B3B4E; border-radius:14px; padding:14px; }
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
.chain-end { margin:10px 0 0; padding:10px 14px; border:1px dashed var(--line); border-radius:14px; background:var(--surface);
  font-size:14px; font-weight:600; color:var(--ink); }
.chain-end .arrow { color:var(--blue); margin-right:4px; }
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

/* Live comparison */
.st-key-lablock { max-width:480px; margin:0 auto; width:100%; }
.current-box { background:var(--ink); color:#fff; border-radius:14px; padding:16px; height:100%; }
.current-box .label { color:#AEB6C2; }
.cb-name { font-size:18px; font-weight:600; margin-bottom:6px; }
.cb-id { font-size:13px; color:#C9CFD8; word-break:break-all; }
[class*="st-key-candbox_"] { border:1px solid var(--line); border-radius:14px; padding:12px 16px; background:var(--surface); }
.toolcheck { font-size:13px; font-weight:500; border-radius:8px; padding:6px 10px; }
.toolcheck.ok { color:var(--pass-fg); background:var(--pass-bg); }
.toolcheck.bad { color:var(--soft-fg); background:var(--soft-bg); }
.st-key-addcand button { border-style:dashed; }
.runbar { background:var(--ground); border:1px solid var(--line); border-radius:12px; padding:12px 14px; margin:8px 0; font-size:14px; }
.tiles4 { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:12px; margin:0 0 12px; }
.ctile { border-radius:14px; padding:14px; border:1px solid var(--line); background:var(--surface); }
.ctile .big { font-size:32px; font-weight:600; line-height:1.1; }
.ctile.hard { background:var(--hard); border-color:var(--hard); color:#fff; }
.ctile.hard .label { color:#fff; opacity:.85; }
.ctile.pass { background:var(--pass-bg); color:var(--pass-fg); border-color:var(--pass-bg); }
.ctile.pass .label { color:var(--pass-fg); }
.ctile.partial { background:var(--part-bg); color:var(--part-fg); border-color:var(--part-bg); }
.ctile.partial .label { color:var(--part-fg); }
.brk-row { font-size:14px; padding:6px 0; border-bottom:1px solid var(--line); word-break:break-word; }

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
  .tiles4 { grid-template-columns:repeat(2, minmax(0,1fr)); }
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
