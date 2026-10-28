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


def _fmt(value, unit: str = "") -> str:
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:g}{unit}"
    return str(value) or "–"


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


def _num(value, unit: str) -> str:
    if value is None:
        return "– °C" if "°C" in unit else "–"  # keep "temperature · rain" readable when one is missing
    return f"{value:g}{unit}"


def _chip(state: str, text: str) -> str:
    return f'<span class="xr-chip {state}">{escape(text)}</span>'


def _arrow(chip: str) -> str:
    return f'<div class="xr-arrow"><span class="xr-arrowhead" aria-hidden="true"></span>{chip}</div>'


def _numbers_chip(r: dict) -> str:
    result = r["numbers"]["result"]
    if result == "pass":
        return _chip("match", "✓ numbers match")
    if result == "fail":
        return _chip("mismatch", "✗ numbers changed")
    return _chip("unknown", "– numbers not checked")


def _rules_chip(r: dict) -> str:
    state = answer.rules_badge(r["tool"], r["advice"])["state"]
    text = {"match": "✓ rules match", "mismatch": "✗ rules don't match",
            "unknown": "– rules can't be checked"}[state]
    return _chip(state, text)


def _weather_box(r: dict, condition_word: str) -> str:
    tool = r["tool"]
    return f"""<div class="xr-box">
  <div class="xr-kicker">Weather data</div>
  <div class="xr-main">{_num(tool.get("temperature_c"), " °C")} · rain {_num(tool.get("rain_chance_pct"), "%")}</div>
  <div class="xr-under">{escape(condition_word or "–")}</div>
</div>"""


def _agent1_box(r: dict) -> str:
    tool, summary = r["tool"], r["summary"]
    changed = differing_fields(tool, summary) & {"temperature_c", "rain_chance_pct"}

    def value(key: str, unit: str, prefix: str = "") -> str:
        shown = f"{prefix}{_num(summary.get(key), unit)}"
        if key not in changed:
            return escape(shown)
        return (f'<span class="xr-changed">{escape(shown)} '
                f'<em>was {escape(_num(tool.get(key), unit))}</em></span>')

    flagged = bool(changed) or r["numbers"]["result"] == "fail"
    data_ok = "data ok" if summary.get("data_ok") else "data not ok"
    return f"""<div class="xr-box{' changed' if flagged else ''}">
  <div class="xr-kicker">Agent 1 handed over</div>
  <div class="xr-main">{value("temperature_c", " °C")} · {value("rain_chance_pct", "%", "rain ")}</div>
  <div class="xr-under{'' if summary.get('data_ok') else ' warn'}">{data_ok}</div>
</div>"""


def _agent2_box(r: dict) -> str:
    a = r["advice"]
    jacket = "take jacket" if a["jacket"] else "no jacket"
    umbrella = "take umbrella" if a["umbrella"] else "no umbrella"
    return f"""<div class="xr-box">
  <div class="xr-kicker">Agent 2 decided</div>
  <div class="xr-main">{jacket} · {umbrella}</div>
  <div class="xr-under{'' if a['confident'] else ' warn'}">{'confident' if a['confident'] else 'not confident'}</div>
</div>"""


def _field_list(title: str, data: dict) -> str:
    rows = "".join(f'<div><span>{escape(str(k))}</span><b>{escape(_fmt(v))}</b></div>' for k, v in data.items())
    return f'<div class="xr-fields-col"><div class="xr-kicker">{title}</div><div class="xr-lines">{rows}</div></div>'


def chain_html(r: dict, condition_word: str) -> str:
    """How this answer was made: three boxes with the two checks on the arrows, then All fields."""
    fields = (_field_list("Weather data · get_weather", r["tool"]) + _field_list("Agent 1 summary", r["summary"])
              + _field_list("Agent 2 advice", r["advice"]))
    return f"""<div class="xr-chain">
  <div class="xr-chain-title">How this answer was made</div>
  <div class="xr-row">{_weather_box(r, condition_word)}{_arrow(_numbers_chip(r))}{_agent1_box(r)}{_arrow(_rules_chip(r))}{_agent2_box(r)}</div>
  <details class="xr-all"><summary>All fields</summary><div class="xr-fields">{fields}</div></details>
</div>"""


def xray_html(r: dict, layout: str, open_: bool | None = None, condition_word: str = "") -> str:
    """One X-ray copy. layout is "desk" (shown from 900 px, open by default) or "phone" (folded by default)."""
    open_ = layout == "desk" if open_ is None else open_
    return f"""<div class="xr xr-{layout}">
  <div class="xr-stack">{answer_card(r)}<div class="xr-peek" aria-hidden="true"><i></i><i></i><i></i></div></div>
  <details class="xr-details"{' open' if open_ else ''}>
    <summary class="xr-btn"><span class="xr-when-closed">X-ray this answer</span><span class="xr-when-open">Close X-ray</span></summary>
    <div class="xr-layers">{chain_html(r, condition_word)}</div>
  </details>
</div>"""


def today_html(r: dict, mood: str, location: dict, condition_word: str) -> str:
    return (f'<style>{TODAY_CSS}</style>{sky_html(mood)}'
            f'<div class="wt-today {"sky-dark" if is_dark(mood) else "sky-light"}" style="--sky-ink:{ink(mood)}">'
            f'{hero_html(r, location, condition_word)}{xray_html(r, "desk", condition_word=condition_word)}'
            f'{xray_html(r, "phone", condition_word=condition_word)}</div>')


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
.stApp:has([data-testid="stTabPanel"][aria-labelledby] .wt-sky) .st-key-footer_line {
  background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-radius:20px; padding:16px 20px; max-width:760px; margin:0 auto; }

.wt-today { position:relative; z-index:1; max-width:760px; margin:8px auto 16px; color:#0F1B2A;
  font-family:'Geist', system-ui, sans-serif; }
.wt-today .mono, .xr-lines, .ans-label { font-family:'Geist Mono', ui-monospace, monospace; }

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

/* Unfolded: the compact chain */
.xr-layers { margin-top:16px; }
details[open] .xr-layers { animation:xr-open .65s cubic-bezier(.2,.8,.2,1); }
@keyframes xr-open { from { opacity:0; transform:translateY(-28px); } to { opacity:1; transform:none; } }
.xr-chain { background:rgba(255,255,255,.88); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-radius:20px; padding:18px 20px; color:#0F1B2A; box-shadow:0 8px 24px rgba(11,92,173,.08); }
.xr-chain-title { font-size:17px; font-weight:700; margin-bottom:14px; }
.xr-row { display:flex; align-items:stretch; gap:0; }
.xr-box { flex:1 1 0; min-width:0; border:1px solid #D3E2F0; border-radius:14px; padding:12px 14px; background:#FFFFFF; }
.xr-box.changed { border:2px solid #EA580C; padding:11px 13px; }
.xr-kicker { font-family:'Geist Mono', ui-monospace, monospace; font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:#5B6B7D; }
.xr-main { font-size:16px; font-weight:700; margin:6px 0 4px; }
.xr-under { font-size:14px; color:#33475B; }
.xr-under.warn { color:#C2410C; font-weight:600; }
.xr-changed { color:#C2410C; }
.xr-changed em { font-style:normal; font-weight:500; font-size:13px; }
.xr-arrow { flex:0 0 128px; min-width:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; padding:0 6px; }
.xr-arrowhead { position:relative; width:100%; height:2px; background:#0B5CAD; }
.xr-arrowhead::after { content:""; position:absolute; right:-1px; top:-5px; border-left:10px solid #0B5CAD;
  border-top:6px solid transparent; border-bottom:6px solid transparent; }
.xr-chip { font-size:12px; font-weight:600; border-radius:10px; padding:2px 8px; order:-1; max-width:100%; text-align:center; line-height:1.3; }
.xr-chip.match { background:#EEF5FC; color:#0B5CAD; border:1px solid #BFD6EE; }
.xr-chip.mismatch { background:#FFF4EC; color:#C2410C; border:1px solid #FDBA8C; }
.xr-chip.unknown { background:#F6F9FC; color:#5B6B7D; border:1px solid #D3E2F0; }
.xr-all { margin-top:14px; }
.xr-all > summary { cursor:pointer; font-size:14px; font-weight:600; color:#0B5CAD; min-height:32px; display:inline-flex; align-items:center; }
.xr-all > summary:focus-visible { outline:3px solid #0B5CAD; outline-offset:2px; border-radius:6px; }
.xr-fields { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:12px; margin-top:8px; }
.xr-fields .xr-kicker { margin-bottom:6px; }
.xr-lines { background:#F6F9FC; border-radius:12px; padding:8px 12px; font-size:13px; }
.xr-lines > div { display:flex; justify-content:space-between; gap:12px; padding:4px 0; border-bottom:1px solid #E3EBF3; }
.xr-lines > div:last-child { border-bottom:none; }
.xr-lines span { color:#5B6B7D; flex:none; }
.xr-lines b { font-weight:500; text-align:right; word-break:break-word; }

/* Open on desktop, folded on phone */
.xr-phone { display:none; }
@media (max-width: 899px) {
  .xr-desk { display:none; }
  .xr-phone { display:block; }
  .td-temp { font-size:64px; }
  .ans-big { font-size:32px; }
  .ans-card { padding:18px; }
  .xr-row { flex-direction:column; }
  .xr-arrow { flex:none; flex-direction:row; justify-content:flex-start; padding:8px 0 8px 18px; gap:10px; }
  .xr-arrowhead { width:2px; height:26px; flex:none; order:-2; }
  .xr-arrowhead::after { right:auto; left:-5px; top:auto; bottom:-1px; border-left:6px solid transparent;
    border-right:6px solid transparent; border-top:10px solid #0B5CAD; border-bottom:0; }
  .xr-chip { order:0; }
  .xr-fields { grid-template-columns:1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .wt-today *, .wt-today *::before, .wt-today *::after { animation:none !important; transition:none !important; }
  .xr:has(details[open]) .ans-card::after { display:none; }
}
"""
