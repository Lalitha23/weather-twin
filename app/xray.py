"""Today's page body: the sky, the big weather, the answer card and the X-ray.

Pure functions that return HTML for st.html. No iframe and no JavaScript:
the X-ray toggle is a native <details>/<summary>, so it gets keyboard focus,
Space and Enter, and its expanded or collapsed state is announced for free.
Two copies are rendered, open on desktop and folded on phone; CSS shows one.
Spec: docs/REDESIGN.md, "Today tab · the sky follows the weather".
"""
from html import escape

from app import answer
from app.report_data import differing_fields
from app.sky import CHIP_DARK, CHIP_LIGHT, SKY_CSS, ink, is_dark, rgba, sky_html

SUMMARY_LINES = (("temperature_c", "temperature", " °C"), ("rain_chance_pct", "rain chance", "%"),
                 ("wind_kph", "wind", " km/h"), ("conditions", "conditions", ""),
                 ("data_ok", "data_ok", ""), ("notes", "notes", ""))


def _fmt(value, unit: str = "") -> str:
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:g}{unit}"
    return str(value) or "–"


def _pills(agent: dict) -> str:
    return (f'<div class="xr-pills"><span>{escape(agent["model"].split("/")[-1])}</span>'
            f'<span>prompt {escape(agent["prompt_version"])}</span></div>')


def _badge(badge: dict, extra_class: str = "") -> str:
    why = f'<span class="xr-badge-why">{escape("; ".join(badge["why"]))}</span>' if badge["why"] else ""
    return f'<div class="xr-badge {badge["state"]} {extra_class}">{escape(badge["text"])}{why}</div>'


def hero_html(r: dict, location: dict, condition_word: str) -> str:
    tool = r["tool"]
    when = answer.weather_time(tool.get("observed_at"))
    place = f'{location["name"]} {location["zip"]}' + (f" · {when}" if when else "")
    temp = "–" if tool.get("temperature_c") is None else f"{round(tool['temperature_c'])}°<span>C</span>"
    return f"""<div class="td-hero">
  <div class="td-chip">{escape(place)}</div>
  <div class="td-now">
    <div><div class="td-temp">{temp}</div>
      <div class="td-cond">{escape(condition_word or "Unknown")}</div></div>
    <div class="td-chip mono">rain {_fmt(tool.get("rain_chance_pct"), "%")}</div>
  </div>
</div>"""


def answer_card(r: dict) -> str:
    a = r["advice"]
    line1, line2 = answer.answer_lines(a)
    warnings = []
    if not a["confident"]:
        warnings.append('<span class="xr-warn-pill">Not confident</span>')
    if r["numbers"]["result"] == "fail":
        warnings.append('<div class="xr-warn">Agent 1 reported different numbers than the tool</div>')
    badge = _badge(answer.rules_badge(r["tool"], a))
    return f"""<section class="ans-card" aria-label="The answer">
  <div class="ans-label">THE ANSWER</div>
  <div class="ans-big"><div>{escape(line1)}</div><div>{escape(line2)}</div></div>
  {"".join(warnings)}
  {badge}
  <p class="ans-why">{escape(a["why"])}</p>
</section>"""


def _yes(v: bool) -> str:
    return "yes" if v else "no"


def _agent2_layer(r: dict) -> str:
    a = r["advice"]
    return f"""<div class="xr-layer">
  <div class="xr-title">Agent 2 decided</div>{_pills(r["agent2"])}
  <div class="xr-lines">
    <div><span>jacket</span><b>{_yes(a["jacket"])}</b></div>
    <div><span>umbrella</span><b>{_yes(a["umbrella"])}</b></div>
    <div><span>confident</span><b class="{'' if a['confident'] else 'warn'}">{_yes(a["confident"])}</b></div>
  </div>
  <p class="xr-why">{escape(a["why"])}</p>
  {_badge(answer.rules_badge(r["tool"], a), "small")}
</div>"""


def _agent1_layer(r: dict) -> str:
    tool, summary = r["tool"], r["summary"]
    changed = differing_fields(tool, summary)
    rows = []
    for key, label, unit in SUMMARY_LINES:
        value = _fmt(summary.get(key), unit)
        if key in changed:
            rows.append(f'<div class="hl"><span>{label}</span><b>{escape(value)} '
                        f'<em>← was {escape(_fmt(tool.get(key), unit))}</em></b></div>')
        else:
            rows.append(f'<div><span>{label}</span><b>{escape(value)}</b></div>')
    if r["numbers"]["result"] == "fail":
        check = '<div class="xr-badge mismatch small">Agent 1 reported different numbers than the tool</div>'
    else:
        check = '<div class="xr-badge match small">✓ numbers match the tool</div>'
    return f"""<div class="xr-layer">
  <div class="xr-title">Agent 1 handed over</div>{_pills(r["agent1"])}
  <div class="xr-lines">{"".join(rows)}</div>
  {check}
</div>"""


def _tool_layer(r: dict) -> str:
    rows = "".join(f'<div><span>{escape(str(k))}</span><b>{escape(_fmt(v))}</b></div>'
                   for k, v in r["tool"].items())
    return f"""<div class="xr-layer">
  <div class="xr-title">Weather data · get_weather</div>
  <div class="xr-sub">Raw tool output from live Open-Meteo</div>
  <div class="xr-lines">{rows}</div>
</div>"""


def xray_html(r: dict, layout: str, open_: bool | None = None) -> str:
    """One X-ray copy. layout is "desk" (shown from 900 px, open by default) or "phone" (folded by default)."""
    open_ = layout == "desk" if open_ is None else open_
    layers = (_agent2_layer(r) + '<div class="xr-handoff">handoff · Agent 2 reads only this</div>'
              + _agent1_layer(r) + _tool_layer(r))
    return f"""<div class="xr xr-{layout}">
  <div class="xr-stack">{answer_card(r)}<div class="xr-peek" aria-hidden="true"><i></i><i></i><i></i></div></div>
  <details class="xr-details"{' open' if open_ else ''}>
    <summary class="xr-btn"><span class="xr-when-closed">X-ray this answer</span><span class="xr-when-open">Close X-ray</span></summary>
    <div class="xr-layers">{layers}</div>
  </details>
</div>"""


def today_html(r: dict, mood: str, location: dict, condition_word: str) -> str:
    return (f'<style>{TODAY_CSS}</style>{sky_html(mood)}'
            f'<div class="wt-today {"sky-dark" if is_dark(mood) else "sky-light"}" style="--sky-ink:{ink(mood)}">'
            f'{hero_html(r, location, condition_word)}{xray_html(r, "desk")}{xray_html(r, "phone")}</div>')


def error_html(message: str) -> str:
    """A friendly card on a cloudy sky. Never a stack trace."""
    return (f'<style>{TODAY_CSS}</style>{sky_html("cloudy")}'
            f'<div class="wt-today sky-light" style="--sky-ink:{ink("cloudy")}">'
            f'<section class="ans-card err" role="status">{escape(message)}</section></div>')


TODAY_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;900&family=Geist+Mono:wght@400;500;600&display=swap');
""" + SKY_CSS + """
/* Today shown: let the sky through, frost the chrome. Only the visible tab panel has aria-labelledby.
   stMain gets its own stacking context, so the sky (z-index -1) sits behind all of its content. */
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky),
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) [data-testid="stAppViewContainer"] { background:transparent; }
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) [data-testid="stMain"] { position:relative; z-index:1; }
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) .st-key-wt_header {
  background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-radius:20px; padding:16px 20px; }
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) .stTabs [role="tablist"] {
  background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-radius:999px; padding:0 14px; width:fit-content; }
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) .st-key-footer_line {
  background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-radius:20px; padding:16px 20px; max-width:760px; margin:0 auto; }

.wt-today { position:relative; z-index:1; max-width:760px; margin:8px auto 16px; color:#0F1B2A;
  font-family:'Geist', system-ui, sans-serif; }
.wt-today .mono, .xr-lines, .xr-pills, .ans-label, .xr-handoff { font-family:'Geist Mono', ui-monospace, monospace; }

/* Frosted chip for small text sitting on the sky (4.5:1 on every mood) */
.td-chip { display:inline-block; font-size:15px; font-weight:500; border-radius:999px; padding:6px 14px;
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px); }
.sky-light .td-chip { background:""" + rgba(CHIP_LIGHT) + """; color:#0F1B2A; }
.sky-dark .td-chip { background:""" + rgba(CHIP_DARK) + """; color:#FFFFFF; }

.td-hero { margin:4px 0 20px; }
.td-now { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; margin-top:14px; }
.td-temp { font-size:76px; font-weight:900; line-height:1; letter-spacing:-.03em; color:var(--sky-ink); }
.td-temp span { font-size:28px; font-weight:700; margin-left:2px; }
.td-cond { font-size:26px; font-weight:700; color:var(--sky-ink); margin-top:4px; }
.sky-dark .td-temp, .sky-dark .td-cond { text-shadow:0 1px 14px rgba(15,27,42,.35); }

/* Answer card and the folded stack */
.xr-stack { position:relative; margin-bottom:52px; transition:margin .65s cubic-bezier(.2,.8,.2,1); }
.ans-card { position:relative; z-index:3; overflow:hidden; background:rgba(255,255,255,.88);
  backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); border-radius:20px; padding:24px;
  box-shadow:0 8px 24px rgba(11,92,173,.08); color:#0F1B2A; }
.ans-card.err { font-size:17px; }
.ans-label { font-size:13px; letter-spacing:.12em; color:#5B6B7D; margin-bottom:8px; }
.ans-big { font-size:40px; font-weight:900; line-height:1.12; letter-spacing:-.02em; margin-bottom:14px; }
.ans-why { font-size:15px; color:#33475B; margin:12px 0 0; }
.xr-warn-pill { display:inline-block; background:#FFF4EC; color:#C2410C; border:1px solid #FDBA8C; border-radius:999px;
  padding:3px 12px; font-size:14px; font-weight:600; margin:0 8px 8px 0; }
.xr-warn { background:#FFF4EC; color:#C2410C; border:1px solid #FDBA8C; border-radius:10px; padding:8px 12px;
  font-size:14px; font-weight:500; margin:0 0 8px; }
.xr-badge { display:inline-block; border-radius:10px; padding:6px 12px; font-size:14px; font-weight:600; }
.xr-badge.match { background:#EEF5FC; color:#0B5CAD; border:1px solid #BFD6EE; }
.xr-badge.mismatch { background:#FFF4EC; color:#C2410C; border:1px solid #FDBA8C; }
.xr-badge.unknown { background:#F6F9FC; color:#5B6B7D; border:1px solid #D3E2F0; }
.xr-badge.small { font-size:13px; padding:4px 10px; margin-top:10px; }
.xr-badge-why { display:block; font-weight:500; font-size:13px; margin-top:2px; }
.xr-peek i { position:absolute; inset:0; border-radius:20px; background:rgba(255,255,255,.88); pointer-events:none;
  transition:transform .65s cubic-bezier(.2,.8,.2,1), opacity .4s; }
.xr-peek i:nth-child(1) { z-index:2; transform:translateY(16px) scale(.94); opacity:.75; }
.xr-peek i:nth-child(2) { z-index:1; transform:translateY(28px) scale(.88); opacity:.5; }
.xr-peek i:nth-child(3) { z-index:0; transform:translateY(40px) scale(.82); opacity:.3; }
.xr:has(details[open]) .xr-stack { margin-bottom:16px; }
.xr:has(details[open]) .xr-peek i { transform:none; opacity:0; }
.xr:has(details[open]) .ans-card::after { content:""; position:absolute; left:0; right:0; top:0; height:2px;
  background:linear-gradient(90deg, rgba(11,92,173,0), #0B5CAD, rgba(11,92,173,0));
  animation:xr-scan 2.6s ease-in-out infinite; }
@keyframes xr-scan { 0% { top:0; opacity:0; } 10% { opacity:1; } 90% { opacity:1; } 100% { top:100%; opacity:0; } }

/* The toggle: a native summary styled as a 48 px button */
.xr-btn { list-style:none; display:flex; align-items:center; justify-content:center; min-height:48px; border-radius:12px;
  background:#0F1B2A; color:#FFFFFF; font-size:16px; font-weight:600; cursor:pointer; border:2px solid #0F1B2A;
  user-select:none; }
.xr-btn::-webkit-details-marker { display:none; }
.xr-btn:focus-visible { outline:3px solid #0B5CAD; outline-offset:3px; box-shadow:0 0 0 6px #FFFFFF; }
.xr-when-open { display:none; }
details[open] > .xr-btn { background:rgba(255,255,255,.88); color:#0B5CAD; border-color:#0B5CAD; }
details[open] > .xr-btn .xr-when-closed { display:none; }
details[open] > .xr-btn .xr-when-open { display:inline; }

/* Unfolded layers */
.xr-layers { position:relative; margin-top:16px; padding-left:18px; }
.xr-layers::before { content:""; position:absolute; left:0; top:6px; bottom:6px; width:2px; background:#0B5CAD;
  border-radius:2px; transform-origin:top; }
details[open] .xr-layers { animation:xr-open .65s cubic-bezier(.2,.8,.2,1); }
details[open] .xr-layers::before { animation:xr-line .65s cubic-bezier(.2,.8,.2,1); }
@keyframes xr-open { from { opacity:0; transform:translateY(-28px); } to { opacity:1; transform:none; } }
@keyframes xr-line { from { transform:scaleY(0); } to { transform:scaleY(1); } }
.xr-layer { background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-radius:20px; padding:18px 20px; margin:0 0 12px; color:#0F1B2A; box-shadow:0 8px 24px rgba(11,92,173,.08); }
.xr-title { font-size:17px; font-weight:700; margin-bottom:8px; }
.xr-sub { font-size:13px; color:#5B6B7D; margin:-4px 0 8px; }
.xr-pills { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }
.xr-pills span { font-size:13px; border:1px solid #D3E2F0; border-radius:999px; padding:2px 10px; background:#F6F9FC; }
.xr-lines { background:#F6F9FC; border-radius:12px; padding:8px 12px; font-size:13px; }
.xr-lines > div { display:flex; justify-content:space-between; gap:12px; padding:4px 0; border-bottom:1px solid #E3EBF3; }
.xr-lines > div:last-child { border-bottom:none; }
.xr-lines span { color:#5B6B7D; flex:none; }
.xr-lines b { font-weight:500; text-align:right; word-break:break-word; }
.xr-lines b.warn { color:#C2410C; }
.xr-lines .hl b { background:#FFEDD5; color:#9A3412; border-radius:4px; padding:0 4px; }
.xr-lines .hl em { font-style:normal; font-weight:600; }
.xr-why { font-size:14px; margin:10px 0 0; color:#33475B; }
.xr-handoff { display:inline-block; font-size:13px; font-weight:600; color:#0B5CAD; background:rgba(255,255,255,.88);
  border-radius:999px; padding:4px 12px; margin:0 0 12px; }

/* Open on desktop, folded on phone */
.xr-phone { display:none; }
@media (max-width: 899px) {
  .xr-desk { display:none; }
  .xr-phone { display:block; }
  .td-temp { font-size:64px; }
  .ans-big { font-size:32px; }
  .ans-card { padding:18px; }
}
@media (prefers-reduced-motion: reduce) {
  .wt-today *, .wt-today *::before, .wt-today *::after { animation:none !important; transition:none !important; }
  .xr:has(details[open]) .ans-card::after { display:none; }
}
"""
