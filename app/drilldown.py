"""Look inside one run: callout, three panels, the last step and the check grid.

Used by the Live comparison. The Official report uses the Handoff Inspector instead.
"""
import streamlit as st

from app import report_data as rd
from app.ui import esc, json_block, md


def _panel(n: int, title: str, body: str, start: int | None) -> str:
    is_start = n == start
    flag = "<em>failure starts here</em>" if is_start else ""
    return f'<div class="panel {"start" if is_start else ""}"><div class="ph"><span>{n} · {title}</span>{flag}</div>{body}</div>'


def render_run(run: dict) -> None:
    checks = run["checks"]
    tool = run["summarizer"]["tool_output"]
    summ = run["summarizer"]["summary"]
    advice = run["advisor"]["advice"]
    start = rd.failure_start(checks)

    md(f'<div class="callout">{esc(rd.callout(checks))}</div>')
    diff = rd.differing_fields(tool, summ)
    p1, p2, p3 = st.columns(3)
    with p1:
        md(_panel(1, "Tool output (twin)", json_block(tool, diff), start))
    with p2:
        body = json_block(summ, diff) if summ is not None else \
            f'<p class="muted">No summary ({esc(run["summarizer"]["error"])})</p>'
        md(_panel(2, "Agent 1 summary", body, start))
    with p3:
        body = json_block(advice, rd.wrong_advice_fields(checks)) if advice is not None else \
            f'<p class="muted">No advice ({esc(run["advisor"]["error"])})</p>'
        md(_panel(3, "Agent 2 advice", body, start))
    md('<div class="chain-end"><span class="arrow">→</span> 4 · His phone or room speaker, later '
       '<span class="muted">· not built yet, nothing is sent</span></div>')

    boxes = []
    for name, c in rd.checks_sorted(checks):
        if c["result"] == "n/a":
            continue
        fail = c["result"] == "fail"
        detail = f"<p>{esc(c['detail'])}</p>" if c["detail"] else ""
        boxes.append(f'<div class="chk {"fail" if fail else ""}"><b>{name}</b>'
                     f'<span class="r">{"Fail" if fail else "Pass"}</span>{detail}</div>')
    md(f'<div class="card" style="margin-top:16px;"><h3>Checks for this run</h3>'
       f'<div class="checks">{"".join(boxes)}</div></div>')
