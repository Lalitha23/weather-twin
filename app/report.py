"""Test Lab, Official report view. No model calls.

Reads only results/matrix_summary.json and results/official_matrix_oct25.jsonl
through app.report_data.
"""
import streamlit as st

from app import report_data as rd
from app.inspector import inspector_data, inspector_html, scenario_expected
from app.ui import esc, md

PICK = ("insp_scenario", "insp_label", "insp_repeat")


@st.cache_data(show_spinner=False)
def _load() -> tuple[dict, list[dict]]:
    return rd.load_summary(), rd.load_runs()


def _intro_line(summary: dict) -> str:
    models = {c["model"] for c in summary["columns"]}
    prompts = {c["prompt_version"] for c in summary["columns"]}
    return (f'{len(rd.scenarios(summary))} scenarios × {len(models)} models × {len(prompts)} prompt versions × '
            f'{summary["repeats"]} repeats. Same agent code as Today, fake weather from the twin. '
            f'Nothing here calls a model.')


def _hero(summary: dict, runs: list[dict], run: dict) -> None:
    n = rd.hero_numbers(runs)
    tail = "This run slipped past one." if rd.failed(run["checks"]) else "This run passed every one."
    md(f"""<div class="hero">
  <div class="kicker">OFFICIAL RUN · {n['runs']} RUNS · {n['broke']} BROKE · {n['first_handoff']} AT THE FIRST HANDOFF</div>
  <h1>Every handoff gets a checkpoint. <span class="tail">{tail}</span></h1>
  <p class="lead">Before two agents tell my son what to wear, each message between them is inspected.
  Pick any of the {n['runs']} official runs.</p>
  <p class="small">{esc(_intro_line(summary))}</p>
</div>""")


def _pick(summary: dict, runs: list[dict], shipped: str) -> dict:
    """Jump buttons and the run picker. Native widgets: a change reruns the page, no model calls."""
    jumps = rd.jump_runs(summary, runs, shipped)
    if PICK[0] not in st.session_state:
        first = jumps[0]
        st.session_state.update(dict(zip(PICK, (first["scenario"], first["label"], first["repeat"]))))

    def jump(j: dict) -> None:
        st.session_state.update(dict(zip(PICK, (j["scenario"], j["label"], j["repeat"]))))

    with st.container(key="jumps"):
        md('<div class="jump-label">Jump to</div>')
        cols = st.columns(len(jumps))
        for col, j in zip(cols, jumps):
            col.button(j["title"], key=f"jump_{j['scenario']}_{j['label']}_{j['repeat']}",
                       on_click=jump, args=(j,), use_container_width=True)
    names = rd.scenarios(summary)
    labels = [c["label"] for c in summary["columns"]]
    with st.container(key="picker"):
        s1, s2, s3 = st.columns(3)
        scenario = s1.selectbox("Scenario", names, key=PICK[0],
                                format_func=lambda s: f"{s}  · held out" if rd.is_held_out(s) else s)
        label = s2.selectbox("Setup", labels, key=PICK[1], format_func=lambda l: rd.column_title(rd.column(summary, l)))
        repeat = s3.selectbox("Repeat", list(range(1, summary["repeats"] + 1)), key=PICK[2])
    col = rd.column(summary, label)
    return rd.find_run(runs, scenario, col["model"], col["prompt_version"], repeat)


def _side_panel(summary: dict, runs: list[dict], shipped: str) -> None:
    c = rd.stat_cards(summary, runs, shipped)
    most = "most of any setup" if c["clean_is_most"] else "every check passed"
    md(f"""<div class="shipped">
  <div class="kicker">SHIPPED TO TODAY</div>
  <div class="sname">{esc(c['name'])}</div>
  <p>Better, not perfect. A later run still repeated the note.</p>
</div>
<div class="stats">
  <div class="stat"><div class="kicker">Clean handoffs</div><b>{c['handoff']['passed']}/{c['handoff']['applicable']}</b>
    <span>up from {c['handoff_baseline']['passed']}/{c['handoff_baseline']['applicable']} with the plain prompt</span></div>
  <div class="stat"><div class="kicker">Numbers kept</div><b>{c['numbers']['passed']}/{c['numbers']['applicable']}</b>
    <span>Agent 1 passed the tool's numbers through</span></div>
  <div class="stat"><div class="kicker">Clean runs</div><b>{c['clean']['passed']}/{c['clean']['applicable']}</b>
    <span>{most}</span></div>
  <div class="stat"><div class="kicker">Cost</div><b>{c['avg_tokens']:,.0f}</b>
    <span>tokens per run on average, median {c['median_latency_s']:.1f} s</span></div>
</div>""")


def _inspector(summary: dict, runs: list[dict], shipped: str, run: dict) -> None:
    left, right = st.columns([13, 7], gap="medium")
    with left, st.container(key="inspector"):
        if run is None:
            md('<div class="card err">That run is not in the official results.</div>')
        else:
            # st.iframe replaces the deprecated components.html. Our own page, with run text passed
            # as JSON and shown with textContent. height="content" follows the page inside.
            st.iframe(inspector_html(inspector_data(run, scenario_expected(run["scenario"]))), height="content")
    with right:
        _side_panel(summary, runs, shipped)


def _what_i_found(summary: dict, runs: list[dict], shipped: str) -> None:
    f = rd.what_i_found(summary, runs, shipped)
    quiet = ""
    if f["quiet"]:
        q = f["quiet"]
        quiet = (f' {esc(q["model"])} with the hardened prompt was sneakier: its summary text looked clean, '
                 f'but in {rd.fmt_count(q["numbers_changed"])} runs it still changed the number and Agent 2 '
                 f'skipped the umbrella. That\'s why Test Lab checks the numbers as well as the text.')
    md(f"""<div class="card">
  <h3>What I found</h3>
  <p style="margin:0;">I hid a fake "units note" in one weather reading. It told Agent 1 the rain chance was inverted.
  {esc(f['model'])} with the plain prompt changed {f['tool_rain']:g}% rain to {f['summary_rain']:g}%. Agent 2, which
  only reads Agent 1's summary, confidently said no umbrella in {rd.fmt_count(f['baseline_obeyed'])} runs.
  With the hardened prompt, {esc(f['model'])} blocked it in {rd.fmt_count(f['shipped_resisted'])} runs.
  In a later lab run it still repeated the hidden note, so v2 is better, not perfect.{quiet}</p>
</div>""")


def _decision(summary: dict, shipped: str) -> None:
    d = rd.decision(summary, shipped)
    t = rd.trade_off(summary, shipped)
    others = " and ".join(f"{c['passed']}" for c in t["other_flagged"][:-1])
    last = t["other_flagged"][-1]
    other_counts = f"{others} and {rd.fmt_count(last)}" if others else rd.fmt_count(last)
    agent2 = ("Agent 2 still lowered its confidence every time." if t["agent2_all_lowered"]
              else "Agent 2 did not always lower its confidence.")
    obeyed = d["other_obeyed"]
    md(f"""<div class="decision">
  <div>
    <div class="label">Decision</div>
    <h2>{esc(d['title'])}</h2>
    <div class="cost">About {d['extra_tokens_rounded']} more tokens per run than v1, median near {d['median_latency_s']} s.</div>
    <div class="cost" style="margin-top:8px;">Trade-off: {esc(t['model'])}'s Agent 1 flagged missing or contradictory
      data in {rd.fmt_count(t['flagged'])} runs ({esc(t['other_model'])}: {other_counts}). {agent2}</div>
    <div class="btn-disabled">Promote to Today · coming later</div>
  </div>
  <div class="reasons">
    <div class="reason"><b>Held out injection resisted {rd.fmt_count(d['holdout_resisted'])}</b>
      <span>Committed after v2. Neither has changed since. {esc(d['other_model'])} obeyed it in {obeyed['passed']} of {obeyed['applicable']} runs.</span></div>
    <div class="reason"><b>Handoff clean in {rd.fmt_count(d['handoff'])} injection runs</b>
      <span>Up from {rd.fmt_count(d['handoff_baseline'])} with v1.</span></div>
    <div class="reason"><b>Numbers matched the tool in {rd.fmt_count(d['numbers'])} runs</b>
      <span>Agent 1 passed the weather through unchanged.</span></div>
  </div>
</div>""")


def _results_table(summary: dict, shipped: str) -> None:
    cols = summary["columns"]
    misleading = set(rd.misleading_columns(summary))
    head = "".join(
        f'<th>{esc(rd.column_title(c))}{"<span class=badge>Shipped</span>" if c["label"] == shipped else ""}</th>'
        for c in cols)
    rows = []
    for check, desc in rd.CHECK_DESCRIPTIONS.items():
        cells = []
        for c in cols:
            count = rd.total(summary, c["label"])["checks"][check]
            cls = rd.cell_class(check, count)
            note = ""
            if check == "handoff_clean" and c["label"] in misleading:
                cls += " misleading"
                note = "<small>text clean, numbers changed</small>"
            cells.append(f'<td class="c {cls}">{rd.fmt_count(count)}{note}</td>')
        rows.append(f'<tr><td class="name">{check}<div>{esc(desc)}</div></td>{"".join(cells)}</tr>')
    md(f"""<div class="card">
  <h3>Results by check</h3>
  <div class="legend"><span><i style="background:var(--pass-bg)"></i>All passed</span>
    <span><i style="background:var(--part-bg)"></i>Some failed</span>
    <span><i style="background:var(--hard)"></i>Handoff or numbers failed</span>
    <span><i style="outline:2px dashed var(--hard);outline-offset:-2px"></i>Text clean, numbers changed</span></div>
  <div class="scroll"><table class="results"><thead><tr><th>Check</th>{head}</tr></thead>
  <tbody>{"".join(rows)}</tbody></table></div>
  <p class="foot">v1 = plain prompt, v2 = hardened prompt. Totals differ because each check applies only to some
  scenarios. Honesty is scored for each agent separately, so the eight checks show as nine rows.</p>
</div>""")


def _cost(summary: dict) -> str:
    rows = "".join(
        f'<tr><td>{esc(rd.column_title(c))}</td>'
        f'<td class="n">{rd.total(summary, c["label"])["avg_total_tokens"]:,.0f}</td>'
        f'<td class="n">{rd.total(summary, c["label"])["median_latency_s"]:.2f} s</td></tr>'
        for c in summary["columns"])
    return f"""<div class="card"><h3>Cost and speed</h3>
  <div class="scroll"><table class="plain"><thead><tr><th>Setup</th><th class="n">Avg tokens</th>
  <th class="n">Median latency</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="foot">Median, not average. One Nemotron v2 call hung for 1,551 s during the official run.
  A 60 s timeout was added afterwards.</p></div>"""


def _no_prompt_fixed(summary: dict) -> str:
    n = rd.no_prompt_fixed(summary)
    agent2 = ("Agent 2 lowered its confidence every time." if n["agent2_all_caught"]
              else "Agent 2 did not always lower its confidence.")
    return f"""<div class="card"><h3>No prompt fixed this</h3>
  <p style="margin:0 0 8px;">Heavy snow at 30 °C. Agent 1 flagged it in {n['agent1_best']} of {n['runs_per_column']}
  runs in every column. {agent2}</p>
  <p class="muted" style="margin:0;">Next step: a plausibility rule in code, not a better prompt.</p></div>"""


def render() -> None:
    summary, runs = _load()
    shipped = rd.active_label(rd.load_active())
    with st.container(key="hero_slot"):
        hero = st.empty()  # filled after the picker, so the headline follows the selected run
    run = _pick(summary, runs, shipped)
    with hero.container():
        if run is not None:
            _hero(summary, runs, run)
    _inspector(summary, runs, shipped, run)
    _what_i_found(summary, runs, shipped)
    _decision(summary, shipped)
    _results_table(summary, shipped)
    c1, c2 = st.columns(2)
    with c1:
        md(_cost(summary))
    with c2:
        md(_no_prompt_fixed(summary))
