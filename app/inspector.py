"""The Handoff Inspector for one official run. Pure functions, no Streamlit, no model calls.

inspector_data() turns a saved run into what the replay shows: four pipeline
nodes, the gate chips, and the four steps. inspector_html() returns a self
contained page for st.iframe. All run text reaches the page
as JSON and is inserted with textContent, so scenario text is only ever shown.
Spec: docs/REDESIGN.md, "The Handoff Inspector".
"""
import json
from pathlib import Path
from typing import Any

from app import report_data as rd

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
STEP2_CHECKS = ("handoff_clean", "numbers_match_tool", "honesty_agent1", "role_adherence")
STEP3_CHECKS = ("umbrella_rule", "jacket_rule", "injection_not_followed", "honesty_agent2", "format_ok")
ALWAYS_SHOWN = ("handoff_clean", "numbers_match_tool")
SUMMARY_LINES = (("temperature_c", "temperature", " °C"), ("rain_chance_pct", "rain chance", "%"),
                 ("wind_kph", "wind", " km/h"), ("conditions", "conditions", ""),
                 ("data_ok", "data_ok", ""), ("notes", "notes", ""))


def scenario_expected(name: str) -> dict:
    """The scenario's own expected block. Read only, for highlighting injected text."""
    path = SCENARIOS / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get("_twin", {}).get("expected", {})


def needles(expected: dict) -> list[str]:
    marker = expected.get("injection_marker")
    return ([marker] if marker else []) + list(expected.get("injection_obeyed_phrases", []))


def split_injected(text: Any, words: list[str]) -> list[str] | None:
    """[clean part, injected part] when text holds injected words, else None.

    The injected part starts at the sentence or bracket that holds the first match,
    so "13:00 (units note: ...)" highlights the whole bracketed note.
    """
    if not isinstance(text, str) or not words:
        return None
    low = text.lower()
    hits = [low.find(w.lower()) for w in words if w and w.lower() in low]
    if not hits:
        return None
    first = min(hits)
    starts = [text.rfind(". ", 0, first) + 2, text.rfind(" (", 0, first) + 1]
    start = max([s for s in starts if s > 0] or [first])
    return [text[:start], text[start:]]


def _fmt(value: Any, unit: str = "") -> str:
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:g}{unit}"
    return str(value) or "–"


def _tool_lines(tool: Any, words: list[str]) -> list[dict]:
    if not isinstance(tool, dict):
        return [{"k": "output", "v": _fmt(tool)}]
    return [{"k": str(k), "v": _fmt(v), "inj": split_injected(v, words)} for k, v in tool.items()]


def _summary_lines(run: dict, words: list[str]) -> list[dict]:
    summary = run["summarizer"]["summary"]
    if summary is None:
        return [{"k": "no summary", "v": str(run["summarizer"].get("error") or "–")}]
    tool = run["summarizer"]["tool_output"] if isinstance(run["summarizer"]["tool_output"], dict) else {}
    changed = rd.differing_fields(tool, summary)
    lines = []
    for key, label, unit in SUMMARY_LINES:
        line = {"k": label, "v": _fmt(summary.get(key), unit), "inj": split_injected(summary.get(key), words)}
        if key in changed:
            line["was"] = _fmt(tool.get(key), unit)
        lines.append(line)
    return lines


def _advice_lines(run: dict) -> list[dict]:
    advice = run["advisor"]["advice"]
    if advice is None:
        return [{"k": "no advice", "v": str(run["advisor"].get("error") or "–")}]
    yes_no = {True: "yes", False: "no"}
    return [{"k": "jacket", "v": yes_no[advice["jacket"]]}, {"k": "umbrella", "v": yes_no[advice["umbrella"]]},
            {"k": "confident", "v": yes_no[advice["confident"]]}, {"k": "why", "v": advice["why"]}]


def _check_boxes(checks: dict, names: tuple[str, ...]) -> list[dict]:
    boxes = []
    for name in names:
        c = checks.get(name)
        if c is None or (c["result"] == "n/a" and name not in ALWAYS_SHOWN):
            continue
        detail = rd.plain_detail(name, c["detail"]) if c["result"] == "fail" else ""
        boxes.append({"name": name, "result": c["result"], "detail": detail})
    return boxes


def _mark(result: str | None) -> str:
    return {"pass": "✓", "fail": "✗"}.get(result or "", "–")


def _gate(results: list[str]) -> str:
    if "fail" in results:
        return "fail"
    return "pass" if "pass" in results else "na"


def _rain(source: Any) -> str:
    if not isinstance(source, dict):
        return "–"
    if "error" in source:
        return "timeout" if "timeout" in str(source["error"]).lower() else "error"
    return f"rain {_fmt(source.get('rain_chance_pct'), '%')}"


def verdict(checks: dict) -> list[str]:
    start = rd.failure_start(checks)
    lines = {2: ["Failure started at Agent 1. Agent 2 only passed it on."],
             3: ["Agent 1 was fine. Failure started at Agent 2."]}.get(start, ["Clean run. Every handoff passed."])
    if checks.get("handoff_clean", {}).get("result") == "pass" and \
            checks.get("numbers_match_tool", {}).get("result") == "fail":
        lines.append("A text check alone would have called this run safe.")
    return lines


def inspector_data(run: dict, expected: dict) -> dict[str, Any]:
    checks = run["checks"]
    words = needles(expected)
    tool, summary, advice = run["summarizer"]["tool_output"], run["summarizer"]["summary"], run["advisor"]["advice"]
    start = rd.failure_start(checks)  # 2 = Agent 1, 3 = Agent 2, None = clean
    tool_rain, summary_rain = _rain(tool), _rain(summary) if summary is not None else "no summary"
    clean = not rd.failed(checks)
    nodes = [
        {"kicker": "TOOL", "name": "get_weather (twin)", "value": tool_rain, "tone": ""},
        {"kicker": "AGENT 1", "name": "Summarizer", "value": summary_rain,
         "tone": "orange" if checks.get("numbers_match_tool", {}).get("result") == "fail" else ""},
        {"kicker": "AGENT 2", "name": "Advisor",
         "value": f"umbrella: {'yes' if advice['umbrella'] else 'no'}" if advice else "no answer", "tone": ""},
        {"kicker": "LATER", "name": "His phone or room speaker, later",
         "value": "safe to send" if clean else "should not send", "tone": "blue" if clean else "orange"},
    ]
    result = {name: c["result"] for name, c in checks.items()}
    decision = _gate([result.get(n) for n in ("umbrella_rule", "jacket_rule", "injection_not_followed")])
    gates = [
        {"label": f"text {_mark(result.get('handoff_clean'))}  numbers {_mark(result.get('numbers_match_tool'))}",
         "state": _gate([result.get("handoff_clean"), result.get("numbers_match_tool")])},
        {"label": f"decision {_mark(decision)}", "state": decision},
        {"label": "delivery", "state": "neutral"},
    ]
    steps = [
        {"title": "What the weather tool returned", "lines": _tool_lines(tool, words), "checks": []},
        {"title": "What Agent 1 handed over", "lines": _summary_lines(run, words),
         "checks": _check_boxes(checks, STEP2_CHECKS)},
        {"title": "What Agent 2 decided", "lines": _advice_lines(run), "checks": _check_boxes(checks, STEP3_CHECKS)},
        {"title": "Verdict", "verdict": verdict(checks), "callout": rd.callout(checks), "checks": []},
    ]
    return {"nodes": nodes, "gates": gates, "steps": steps,
            "start_node": None if start is None else start - 1,  # node index where the failure starts
            "fail_step": start}  # replay step where the bar turns orange


def inspector_html(data: dict) -> str:
    payload = json.dumps(data).replace("</", "<\\/")
    return PAGE.replace("__DATA__", payload)


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;900&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root { --ink:#0F1B2A; --muted:#5B6B7D; --line:#D3E2F0; --inner:#E3EBF3; --code:#F6F9FC; --blue:#0B5CAD;
  --orange:#EA580C; --pass-bg:#EEF5FC; --pass-bd:#BFD6EE; --fail-bg:#FFF4EC; --fail-bd:#FDBA8C; --fail-fg:#C2410C;
  --hl-bg:#FFEDD5; --hl-fg:#9A3412; }
* { box-sizing:border-box; }
html, body { margin:0; background:transparent; color:var(--ink); font-family:'Geist', system-ui, sans-serif; font-size:15px; }
.mono { font-family:'Geist Mono', ui-monospace, monospace; }
.card { background:#fff; border:1px solid var(--line); border-radius:20px; box-shadow:0 8px 24px rgba(11,92,173,.08); }
.pipe { padding:14px 16px 16px; margin-bottom:12px; }
.row { display:flex; align-items:stretch; gap:0; padding-top:34px; }  /* the strip above holds the gate chips */
.node { flex:1 1 0; max-width:172px; min-width:0; overflow-wrap:anywhere; border:1px solid var(--line); border-radius:14px; padding:10px 12px;
  background:#fff; transition:border-color .3s, box-shadow .3s; }
.node.active { border:2px solid var(--blue); box-shadow:0 0 0 4px rgba(11,92,173,.15); padding:9px 11px; }
.node.start { border:2px solid var(--orange); padding:9px 11px; }
.node.start.active { box-shadow:0 0 0 4px rgba(234,88,12,.15); }
.kicker { font-size:12px; letter-spacing:.1em; color:var(--muted); }
.nname { font-weight:600; font-size:14px; margin:2px 0 6px; line-height:1.25; }
.nval { font-size:13px; font-weight:600; }
.nval.orange { color:var(--fail-fg); } .nval.blue { color:var(--blue); }
.link { flex:0.55 1 0; min-width:36px; position:relative; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.wire { position:relative; width:100%; height:2px; background:var(--inner); }
.dot { position:absolute; top:-4px; left:0; width:10px; height:10px; border-radius:50%; background:var(--blue);
  animation:travel 1.6s linear infinite; }
.dot.orange { background:var(--orange); }
@keyframes travel { from { left:0; } to { left:calc(100% - 10px); } }
.gate { position:absolute; top:-30px; left:50%; transform:translateX(-50%); white-space:nowrap; z-index:1; font-size:12px; border-radius:999px; padding:2px 8px;
  border:1px solid var(--inner); background:#fff; color:var(--muted); }
.gate.pass { background:var(--pass-bg); border-color:var(--pass-bd); color:var(--blue); }
.gate.fail { background:var(--fail-bg); border-color:var(--fail-bd); color:var(--fail-fg); animation:pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { box-shadow:0 0 0 4px rgba(234,88,12,.18); } }
.gates-phone { display:none; }
.controls { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:0 0 10px; }
button { font:inherit; min-height:44px; border-radius:12px; border:1px solid var(--line); background:#fff; color:var(--ink);
  padding:0 14px; cursor:pointer; font-weight:500; }
button:focus-visible { outline:3px solid var(--blue); outline-offset:2px; }
button.play { background:var(--ink); color:#fff; border-color:var(--ink); min-width:96px; }
button.step[aria-pressed="true"] { border:2px solid var(--blue); color:var(--blue); font-weight:600; }
.bar { height:6px; border-radius:6px; background:var(--inner); overflow:hidden; margin:0 0 12px; }
.fill { height:100%; width:25%; background:var(--blue); transition:width .4s, background .4s; }
.fill.orange { background:var(--orange); }
.panel { padding:18px 20px; height:var(--panel-h, 430px); overflow:auto; }
.ptitle { font-size:12px; letter-spacing:.1em; color:var(--muted); margin-bottom:4px; }
.phead { font-size:20px; font-weight:700; margin:0 0 12px; }
.lines { background:var(--code); border-radius:12px; padding:6px 12px; font-size:13px; }
.line { display:flex; justify-content:space-between; gap:14px; padding:5px 0; border-bottom:1px solid var(--inner); }
.line:last-child { border-bottom:none; }
.line .k { color:var(--muted); flex:none; }
.line .v { text-align:right; word-break:break-word; }
.inj { background:var(--hl-bg); color:var(--hl-fg); border-radius:4px; padding:0 3px; font-weight:600; }
.was { color:var(--hl-fg); font-weight:600; }
.v.changed { background:var(--hl-bg); color:var(--hl-fg); border-radius:4px; padding:0 4px; font-weight:600; }
.checks { display:grid; grid-template-columns:repeat(auto-fill, minmax(190px, 1fr)); gap:8px; margin-top:12px; }
.chk { border-radius:12px; padding:8px 10px; border:1px solid var(--pass-bd); background:var(--pass-bg); color:var(--blue); font-size:13px; }
.chk.fail { background:var(--fail-bg); border-color:var(--fail-bd); color:var(--fail-fg); }
.chk.na { background:var(--code); border-color:var(--inner); color:var(--muted); }
.chk b { font-family:'Geist Mono', ui-monospace, monospace; font-weight:500; }
.chk .r { float:right; font-weight:700; }
.chk p { margin:4px 0 0; color:inherit; }
.verdict { font-size:22px; font-weight:800; line-height:1.25; margin:0 0 8px; }
.verdict + .verdict { font-size:17px; font-weight:600; color:var(--fail-fg); }
.callout { margin-top:14px; border-left:4px solid var(--orange); background:var(--fail-bg); border-radius:10px; padding:10px 14px; }
.callout.clean { border-color:var(--blue); background:var(--pass-bg); }
@media (max-width: 599px) {
  .row { flex-wrap:wrap; gap:10px; }
  .node { flex:1 1 calc(50% - 5px); max-width:none; }
  .link { display:none; }
  .gates-phone { display:flex; flex-wrap:wrap; gap:6px; margin-top:12px; }
  .gates-phone .gate { position:static; transform:none; }
  .row { padding-top:0; }
  .panel { --panel-h:560px; }
}
@media (prefers-reduced-motion: reduce) {
  .dot { display:none; } .gate.fail { animation:none; } .fill, .node { transition:none; }
}
</style></head><body>
<div class="card pipe"><div class="row" id="row"></div><div class="gates-phone" id="gates-phone"></div></div>
<div class="controls" role="group" aria-label="Replay">
  <button class="play" id="play" type="button">Pause</button>
  <button class="step" type="button" data-step="1">1 · Tool</button>
  <button class="step" type="button" data-step="2">2 · Agent 1</button>
  <button class="step" type="button" data-step="3">3 · Agent 2</button>
  <button class="step" type="button" data-step="4">4 · Verdict</button>
</div>
<div class="bar" aria-hidden="true"><div class="fill" id="fill"></div></div>
<div class="card panel" id="panel" aria-live="polite"></div>
<script>
const D = __DATA__;
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let step = 1, playing = !reduced, timer = null;
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function gateEl(g) { return el('span', 'gate mono ' + g.state, g.label); }
const row = document.getElementById('row');
D.nodes.forEach((n, i) => {
  const node = el('div', 'node' + (D.start_node === i ? ' start' : ''));
  node.dataset.i = i;
  node.append(el('div', 'kicker mono', n.kicker), el('div', 'nname', n.name), el('div', 'nval mono ' + n.tone, n.value));
  row.append(node);
  if (i < D.nodes.length - 1) {
    const link = el('div', 'link'), wire = el('div', 'wire'), dot = el('span', 'dot');
    if (D.start_node !== null && i >= D.start_node) dot.classList.add('orange');
    wire.append(dot); link.append(gateEl(D.gates[i]), wire); row.append(link);
  }
});
D.gates.forEach(g => document.getElementById('gates-phone').append(gateEl(g)));
function lines(list) {
  const box = el('div', 'lines mono');
  list.forEach(l => {
    const line = el('div', 'line'), v = el('span', 'v');
    if (l.inj) { v.append(document.createTextNode(l.inj[0]), el('span', 'inj', l.inj[1])); }
    else { v.textContent = l.v; }
    if (l.was !== undefined) { v.classList.add('changed'); v.append(el('span', 'was', '  ← was ' + l.was)); }
    line.append(el('span', 'k', l.k), v); box.append(line);
  });
  return box;
}
function checks(list) {
  const box = el('div', 'checks');
  list.forEach(c => {
    const b = el('div', 'chk ' + (c.result === 'fail' ? 'fail' : c.result === 'n/a' ? 'na' : ''));
    b.append(el('b', null, c.name), el('span', 'r', c.result === 'fail' ? 'Fail' : c.result === 'n/a' ? 'n/a' : 'Pass'));
    if (c.detail) b.append(el('p', null, c.detail));
    box.append(b);
  });
  return box;
}
function render() {
  const s = D.steps[step - 1], panel = document.getElementById('panel');
  panel.replaceChildren(el('div', 'ptitle mono', 'STEP ' + step + ' OF 4'), el('h2', 'phead', s.title));
  if (s.lines) panel.append(lines(s.lines));
  if (s.verdict) {
    s.verdict.forEach(v => panel.append(el('p', 'verdict', v)));
    panel.append(el('div', 'callout' + (D.fail_step ? '' : ' clean'), s.callout));
  }
  if (s.checks.length) panel.append(checks(s.checks));
  document.querySelectorAll('.node').forEach(n => n.classList.toggle('active', +n.dataset.i === step - 1));
  document.querySelectorAll('button.step').forEach(b => b.setAttribute('aria-pressed', +b.dataset.step === step));
  const fill = document.getElementById('fill');
  fill.style.width = (step * 25) + '%';
  fill.classList.toggle('orange', D.fail_step !== null && step >= D.fail_step);
}
function tick() { step = step % 4 + 1; render(); }
function setPlaying(on) {
  playing = on; clearInterval(timer);
  if (on) timer = setInterval(tick, 1800);
  const p = document.getElementById('play'); p.textContent = on ? 'Pause' : 'Play'; p.setAttribute('aria-pressed', on);
}
document.getElementById('play').onclick = () => setPlaying(!playing);
document.querySelectorAll('button.step').forEach(b => b.onclick = () => { setPlaying(false); step = +b.dataset.step; render(); });
render(); setPlaying(playing);
</script></body></html>"""
