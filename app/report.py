"""Test Lab, Official report view. No model calls.

Reads only results/matrix_summary.json and results/official_matrix_oct25.jsonl
through app.report_data.
"""
import streamlit as st

from app import report_data as rd
from app.drilldown import render_run
from app.ui import esc, md


@st.cache_data(show_spinner=False)
def _load() -> tuple[dict, list[dict]]:
    return rd.load_summary(), rd.load_runs()


def _intro(summary: dict, runs: list[dict]) -> None:
    models = {c["model"] for c in summary["columns"]}
    prompts = {c["prompt_version"] for c in summary["columns"]}
    md(f'<p class="muted" style="margin:4px 0 16px;">Official run, Oct 25. {len(runs)} runs: '
       f'{len(rd.scenarios(summary))} scenarios × {len(models)} models × {len(prompts)} prompt versions × '
       f'{summary["repeats"]} repeats. Same agent code as Today, fake weather from the twin. '
       f'Nothing here calls a model.</p>')


def _decision(summary: dict, shipped: str) -> None:
    d = rd.decision(summary, shipped)
    obeyed = d["other_obeyed"]
    md(f"""<div class="decision">
  <div>
    <div class="label">Decision</div>
    <h2>{esc(d['title'])}</h2>
    <div class="cost">About {d['extra_tokens_rounded']} more tokens per run than v1, median near {d['median_latency_s']} s.</div>
    <div class="btn-disabled">Promote to Today · coming later</div>
  </div>
  <div class="reasons">
    <div class="reason"><b>Held out injection resisted {rd.fmt_count(d['holdout_resisted'])}</b>
      <span>Written after v2 was frozen. {esc(d['other_model'])} obeyed it in {obeyed['passed']} of {obeyed['applicable']} runs.</span></div>
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
                note = "<small>misleading alone</small>"
            cells.append(f'<td class="c {cls}">{rd.fmt_count(count)}{note}</td>')
        rows.append(f'<tr><td class="name">{check}<div>{esc(desc)}</div></td>{"".join(cells)}</tr>')
    md(f"""<div class="card">
  <h3>Results by check</h3>
  <div class="legend"><span><i style="background:var(--pass-bg)"></i>All passed</span>
    <span><i style="background:var(--part-bg)"></i>Some failed</span>
    <span><i style="background:var(--hard)"></i>Handoff or numbers failed</span>
    <span><i style="outline:2px dashed var(--hard);outline-offset:-2px"></i>Misleading alone</span></div>
  <div class="scroll"><table class="results"><thead><tr><th>Check</th>{head}</tr></thead>
  <tbody>{"".join(rows)}</tbody></table></div>
</div>""")


def _run_trace(summary: dict, runs: list[dict], shipped: str) -> None:
    md('<div class="card" style="margin-bottom:8px;"><h3>Look inside a run</h3>'
       '<p class="muted" style="margin:0;">Pick any run from the official matrix and follow it through both agents.</p></div>')
    names = rd.scenarios(summary)
    d_scenario, d_label, d_repeat = rd.default_run(summary, runs, shipped)
    labels = [c["label"] for c in summary["columns"]]
    s1, s2, s3 = st.columns(3)
    scenario = s1.selectbox("Scenario", names, index=names.index(d_scenario),
                            format_func=lambda s: f"{s}  · held out" if rd.is_held_out(s) else s)
    label = s2.selectbox("Setup", labels, index=labels.index(d_label),
                         format_func=lambda l: rd.column_title(rd.column(summary, l)))
    repeat = s3.selectbox("Repeat", list(range(1, summary["repeats"] + 1)), index=d_repeat - 1)

    col = rd.column(summary, label)
    run = rd.find_run(runs, scenario, col["model"], col["prompt_version"], repeat)
    if run is None:
        md('<div class="card err">That run is not in the official results.</div>')
        return
    render_run(run)


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
    agent2 = "Agent 2 caught it every time." if n["agent2_all_caught"] else "Agent 2 did not always catch it."
    return f"""<div class="card"><h3>No prompt fixed this</h3>
  <p style="margin:0 0 8px;">Heavy snow at 30 °C. Agent 1 flagged it in {n['agent1_best']} of {n['runs_per_column']}
  runs in every column. {agent2}</p>
  <p class="muted" style="margin:0;">Next step: a plausibility rule in code, not a better prompt.</p></div>"""


def render() -> None:
    summary, runs = _load()
    shipped = rd.active_label(rd.load_active())
    _intro(summary, runs)
    _decision(summary, shipped)
    _results_table(summary, shipped)
    _run_trace(summary, runs, shipped)
    c1, c2 = st.columns(2)
    with c1:
        md(_cost(summary))
    with c2:
        md(_no_prompt_fixed(summary))
