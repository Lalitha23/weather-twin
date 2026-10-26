"""Test Lab, Live comparison: current setup versus up to three candidates.

Behind the same shared password as Today. Runs are fresh, on the twin, with
the scenario passed to the tool directly. Each comparison is saved to
results/lab_<timestamp>.jsonl; the official files are never touched.
"""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from app import report_data as rd
from app.drilldown import render_run
from app.today import ALIASES, lock_card
from app.ui import esc, md
from runner import compare
from runner.run_matrix import scored_scenarios

PACIFIC = ZoneInfo("America/Los_Angeles")
LOCK_TEXT = ("The live comparison runs fresh agents on Nebius Token Factory. "
             "The password keeps strangers from spending your credits.")
TILE_CLASS = {"newly_broken": "hard", "fixed": "pass", "still_failing": "partial", "still_passing": "neutral"}


@st.cache_data(ttl=3600, show_spinner=False)
def _models() -> list[str]:
    return compare.list_models()


@st.cache_data(ttl=3600, show_spinner=False)
def _tool_check(model: str) -> dict:
    return compare.tool_call_check(model)


def _setup(key: str, model: str, prompt: str) -> dict:
    return {"key": key, "name": f"{rd.short_name(model)} {prompt}", "model": model, "prompt_version": prompt}


def _current() -> dict | None:
    active = rd.load_active()
    alias = active["model"]
    model = os.getenv(ALIASES[alias], "") if alias in ALIASES else alias
    return _setup("current", model, active["prompt_version"]) if model else None


def _stamp(path: Path) -> str:
    raw = path.stem.removeprefix("lab_")
    try:
        when = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC"))
        return when.astimezone(PACIFIC).strftime("%a %b %-d, %H:%M:%S")
    except ValueError:
        return raw


# ---------- set up ----------

def _candidate_box(i: int, models: list[str], versions: list[str], current: dict) -> dict:
    with st.container(key=f"candbox_{i}"):
        md(f'<div class="label">Candidate {i}</div>')
        others = [m for m in models if m != current["model"]]
        compare_model = os.getenv("COMPARE_MODEL", "")
        default = compare_model if i == 1 and compare_model in models else \
            (others[(i - 1) % len(others)] if others else models[0])
        model = st.selectbox("Model", models, index=models.index(default), key=f"cand_model_{i}")
        prompt = st.selectbox("Prompt", versions, index=versions.index("v2") if "v2" in versions else 0,
                              key=f"cand_prompt_{i}")
        if model == current["model"]:
            check = {"ok": True, "label": "Same model as current · tool calls work", "reason": ""}
        else:
            with st.spinner("Checking tool calls…"):
                check = _tool_check(model)
        cls, icon = ("ok", "✓") if check["ok"] else ("bad", "✕")
        md(f'<div class="toolcheck {cls}">{icon} {esc(check["label"])}</div>')
    return {**_setup(f"candidate_{i}", model, prompt), "tool_check": check}


def _set_up(current: dict) -> None:
    settings = compare.lab_settings()
    try:
        models = _models()
    except Exception:
        md('<div class="card err">Couldn\'t load the model list from Token Factory. Try again in a minute.</div>')
        return
    versions = compare.prompt_versions()
    n = st.session_state.setdefault("n_cand", 1)

    with st.container(key="setup"):
        md('<h3 style="margin:0 0 12px;font-size:18px;">Set up a comparison</h3>')
        cols = st.columns(1 + n)
        with cols[0]:
            md(f'<div class="current-box"><div class="label">Current · what Today runs</div>'
               f'<div class="cb-name">{esc(rd.long_name(current["model"]))}</div>'
               f'<div class="mono cb-id">{esc(current["model"])}</div>'
               f'<div class="mono cb-id">prompt {esc(current["prompt_version"])}</div></div>')
        candidates = []
        for i in range(1, n + 1):
            with cols[i]:
                candidates.append(_candidate_box(i, models, versions, current))

        b1, b2 = st.columns(2)
        with b1, st.container(key="addcand"):
            if st.button(f"+ Add candidate · up to {settings['max_candidates']}",
                         disabled=n >= settings["max_candidates"], use_container_width=True):
                st.session_state["n_cand"] = n + 1
                st.rerun()
        with b2:
            if n > 1 and st.button("Remove last candidate", use_container_width=True):
                st.session_state["n_cand"] = n - 1
                st.rerun()

        names = list(scored_scenarios())
        scenarios = st.pills("Scenarios", names, selection_mode="multi", default=names, key="lab_scen")
        repeats = st.selectbox("Repeats", [1, 2, 3], index=2, key="lab_repeats")

        runnable = [c for c in candidates if c["tool_check"]["ok"]]
        skipped = [c for c in candidates if not c["tool_check"]["ok"]]
        setups = [current] + runnable
        est = compare.estimate(setups, scenarios or [], repeats, rd.load_summary())
        guessed = f' · new setups estimated from the official average' if est["guessed"] else ""
        skip_note = (f'<div class="toolcheck bad" style="margin-top:6px;">Skipped: '
                     f'{esc(", ".join(c["model"] for c in skipped))}</div>') if skipped else ""
        md(f'<div class="runbar"><b class="mono">{est["runs"]} runs</b> · current and {len(runnable)} '
           f'candidate{"s" if len(runnable) != 1 else ""} × {len(scenarios or [])} scenarios × {repeats} '
           f'repeats · about <span class="mono">{est["tokens"]:,}</span> tokens{guessed}{skip_note}</div>')
        go = st.button("Run comparison", type="primary", use_container_width=True,
                       disabled=not runnable or not scenarios)

    if go:
        _run(current, runnable, skipped, scenarios, repeats)


def _run(current: dict, candidates: list[dict], skipped: list[dict],
         scenarios: list[str], repeats: int) -> None:
    setups = [current] + [{k: v for k, v in c.items() if k != "tool_check"} for c in candidates]
    bar = st.progress(0.0, text="Starting…")
    lines = []
    try:
        for done, total, line in compare.run_comparison(setups, scenarios, repeats):
            lines.append(line)
            bar.progress(done / total, text=f"{done} of {total} runs")
    except Exception:
        md('<div class="card err">The comparison stopped partway. Try again in a minute.</div>')
        return
    meta = {"created_at": datetime.now(PACIFIC).isoformat(timespec="seconds"),
            "current": current, "candidates": setups[1:], "scenarios": scenarios,
            "repeats": repeats, "skipped": [c["model"] for c in skipped]}
    path = compare.save_lab_run(meta, lines)
    st.session_state["lab_file"] = path.name
    st.session_state.pop("lab_drill", None)
    bar.empty()


# ---------- results ----------

def _count(c: dict) -> str:
    return f'{c["passed"]} of {c["applicable"]}'


def _group_table(rows: list[dict]) -> str:
    body = "".join(f'<tr><td>{esc(r["scenario"])}</td><td class="mono">{r["check"]}</td>'
                   f'<td class="n">{_count(r["current"])}</td><td class="n">{_count(r["candidate"])}</td></tr>'
                   for r in rows)
    return (f'<div class="scroll"><table class="plain"><thead><tr><th>Scenario</th><th>Check</th>'
            f'<th class="n">Current</th><th class="n">Candidate</th></tr></thead><tbody>{body}</tbody></table></div>')


def _drill(lines: list[dict], meta: dict, cand: dict, drill: dict) -> None:
    md(f'<div class="card" style="margin:16px 0 8px;"><h3>Look inside a run</h3>'
       f'<p class="muted" style="margin:0;">{esc(drill["scenario"])} · <span class="mono">{drill["check"]}</span></p></div>')
    sides = {"candidate": cand, "current": meta["current"]}
    c1, c2 = st.columns(2)
    side = c1.selectbox("Setup", list(sides), format_func=lambda s: f'{s.capitalize()} · {sides[s]["name"]}',
                        key=f"drill_side_{cand['key']}")
    key = sides[side]["key"]
    runs = sorted((l for l in lines if l["setup"] == key and l["scenario"] == drill["scenario"]),
                  key=lambda l: l["repeat"])
    failing = [l["repeat"] for l in runs if l["checks"][drill["check"]]["result"] == "fail"]
    repeats = [l["repeat"] for l in runs]
    default = failing[0] if failing else repeats[0]
    repeat = c2.selectbox("Repeat", repeats, index=repeats.index(default), key=f"drill_rep_{cand['key']}")
    render_run(next(l for l in runs if l["repeat"] == repeat))


def _result_card(path: Path, meta: dict, lines: list[dict], cand: dict) -> None:
    groups = compare.classify(lines, "current", cand["key"])
    cur_cost, cand_cost = compare.cost(lines, "current"), compare.cost(lines, cand["key"])
    with st.container(key=f"result_{cand['key']}"):
        md(f'<h3 style="margin:0 0 4px;font-size:18px;">Current versus {esc(cand["model"].split("/")[-1])} · '
           f'{esc(cand["prompt_version"])}</h3><p class="muted" style="margin:0 0 12px;">'
           f'A cell passes only if every repeat passed.</p>')
        tiles = "".join(f'<div class="ctile {TILE_CLASS[g]}"><div class="label">{compare.GROUP_TITLES[g]}</div>'
                        f'<div class="big mono">{len(groups[g])}</div></div>' for g in compare.GROUPS)
        md(f'<div class="tiles4">{tiles}</div>')

        broken = groups["newly_broken"]
        md(f'<div class="label" style="margin-top:8px;">Newly broken · {len(broken)}</div>')
        if not broken:
            md('<p class="muted" style="margin:0 0 8px;">Nothing passed before and fails now.</p>')
        for i, r in enumerate(broken):
            left, right = st.columns([4, 1.3], vertical_alignment="center")
            left.markdown(
                f'<div class="brk-row"><span>{esc(r["scenario"])}</span> <span class="mono">{r["check"]}</span>'
                f'<span class="mono muted"> · current {_count(r["current"])} → candidate {_count(r["candidate"])}</span></div>',
                unsafe_allow_html=True)
            if right.button("See the run", key=f"see_{cand['key']}_{i}", use_container_width=True):
                st.session_state["lab_drill"] = {"file": path.name, "cand": cand["key"],
                                                 "scenario": r["scenario"], "check": r["check"]}
        for g in ("fixed", "still_failing", "still_passing"):
            with st.expander(f"{compare.GROUP_TITLES[g]} · {len(groups[g])}"):
                md(_group_table(groups[g]) if groups[g] else '<p class="muted">None.</p>')

        md(f'''<div class="scroll" style="margin-top:12px;"><table class="plain"><thead><tr><th>Cost and speed</th>
  <th class="n">Avg tokens</th><th class="n">Median latency</th></tr></thead><tbody>
  <tr><td>Current · {esc(meta["current"]["name"])}</td><td class="n">{cur_cost["avg_total_tokens"]:,.0f}</td>
  <td class="n">{cur_cost["median_latency_s"]:.2f} s</td></tr>
  <tr><td>Candidate · {esc(cand["name"])}</td><td class="n">{cand_cost["avg_total_tokens"]:,.0f}</td>
  <td class="n">{cand_cost["median_latency_s"]:.2f} s</td></tr></tbody></table></div>''')

    drill = st.session_state.get("lab_drill")
    if drill and drill["file"] == path.name and drill["cand"] == cand["key"]:
        _drill(lines, meta, cand, drill)


def _results() -> None:
    files = compare.list_lab_runs()
    if not files:
        md('<div class="card"><h3>Results</h3><p class="muted" style="margin:0;">No lab runs yet. '
           'Set up a comparison above and run it.</p></div>')
        return
    names = [f.name for f in files]
    chosen = st.session_state.get("lab_file")
    head, pick = st.columns([3, 2], vertical_alignment="bottom")
    head.markdown('<h3 style="margin:16px 0 0;font-size:20px;">Results</h3>', unsafe_allow_html=True)
    name = pick.selectbox("Past lab runs", names, index=names.index(chosen) if chosen in names else 0,
                          format_func=lambda n: _stamp(Path(n)), key="lab_past")
    st.session_state["lab_file"] = name
    path = compare.RESULTS / name
    meta, lines = compare.load_lab_run(path)

    md('<p class="foot" style="margin:0 0 8px;">Lab runs are kept on this server only. On Streamlit Cloud they '
       'vanish when the app restarts, so download any you want to keep. They never change the official report.</p>')
    st.download_button("Download results", data=path.read_bytes(), file_name=path.name,
                       mime="application/jsonl", key=f"dl_{name}")
    if meta.get("skipped"):
        md(f'<div class="toolcheck bad">Skipped as unsupported: {esc(", ".join(meta["skipped"]))}</div>')
    for cand in meta["candidates"]:
        _result_card(path, meta, lines, cand)


def render() -> None:
    if not st.session_state.get("unlocked"):
        with st.container(key="lablock"):
            lock_card("lab", LOCK_TEXT)
        return
    md('<p class="muted" style="margin:4px 0 16px;">Try a new setup against the one Today runs. Same agents, '
       'same scenarios, fresh runs. This spends Token Factory credits.</p>')
    current = _current()
    if current is None:
        md('<div class="card err">The live comparison isn\'t set up yet. The current model setting is missing.</div>')
        return
    _set_up(current)
    _results()
