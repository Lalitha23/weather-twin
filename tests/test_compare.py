"""Comparison engine. Stub clients and stub runs, no API calls."""
import json
from types import SimpleNamespace

import pytest

from runner import compare

CUR = {"key": "current", "name": "Nemotron v2", "model": "nvidia/Nemotron-3-Ultra-550b-a55b",
       "prompt_version": "v2"}
CAND = {"key": "candidate_1", "name": "gpt-oss v2", "model": "openai/gpt-oss-120b",
        "prompt_version": "v2"}
SETTINGS = {"workers": 2, "rate_limit_retries": 2, "retry_wait_s": 5}


def line(setup, scenario, results):
    """A scored run line with the given check results; other checks n/a."""
    checks = {n: {"result": "n/a", "detail": ""} for n in compare.CHECKS}
    checks.update({n: {"result": r, "detail": ""} for n, r in results.items()})
    return {"setup": setup, "scenario": scenario, "checks": checks}


def test_classify_four_groups_and_every_repeat_rule():
    lines = [
        # newly broken: current 2 of 2, candidate 1 of 2
        line("current", "s", {"format_ok": "pass"}), line("current", "s", {"format_ok": "pass"}),
        line("candidate_1", "s", {"format_ok": "pass"}), line("candidate_1", "s", {"format_ok": "fail"}),
    ]
    lines += [
        line("current", "t", {"umbrella_rule": "fail", "jacket_rule": "fail", "role_adherence": "pass"}),
        line("candidate_1", "t", {"umbrella_rule": "pass", "jacket_rule": "fail", "role_adherence": "pass"}),
    ]
    g = compare.classify(lines, "current", "candidate_1")
    assert [(r["scenario"], r["check"]) for r in g["newly_broken"]] == [("s", "format_ok")]
    assert g["newly_broken"][0]["candidate"] == {"passed": 1, "applicable": 2}
    assert [r["check"] for r in g["fixed"]] == ["umbrella_rule"]
    assert [r["check"] for r in g["still_failing"]] == ["jacket_rule"]
    assert [r["check"] for r in g["still_passing"]] == ["role_adherence"]


def test_classify_skips_cells_not_applicable_on_both_sides():
    lines = [line("current", "s", {"handoff_clean": "pass"}), line("candidate_1", "s", {})]
    assert all(not rows for rows in compare.classify(lines, "current", "candidate_1").values())


def test_filter_models_hides_non_chat_and_lists_nemotron_first():
    ids = ["openai/gpt-oss-120b", "BAAI/bge-embed-large", "black-forest-labs/flux-dev",
           "meta/llama-guard-3", "nvidia/Nemotron-reward", "nvidia/Nemotron-3-Ultra-550b-a55b",
           "Qwen/Qwen3-Image", "nvidia/nemotron-nano-9b"]
    assert compare.filter_models(ids) == [
        "nvidia/Nemotron-3-Ultra-550b-a55b", "nvidia/nemotron-nano-9b", "openai/gpt-oss-120b"]


def test_prompt_versions_from_files():
    assert compare.prompt_versions() == ["v1", "v2"]


def stub_client(message):
    choice = SimpleNamespace(message=message)
    create = lambda **kw: SimpleNamespace(choices=[choice])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_tool_call_check_outcomes():
    ok = compare.tool_call_check("m", stub_client(SimpleNamespace(tool_calls=[object()], content=None)))
    assert ok["ok"] and ok["label"] == "Real tool calls work"
    text = compare.tool_call_check("m", stub_client(SimpleNamespace(
        tool_calls=None, content='{"name": "get_weather", "arguments": {}}')))
    assert not text["ok"] and "wrote the tool call as text" in text["label"]
    none = compare.tool_call_check("m", stub_client(SimpleNamespace(tool_calls=None, content="Sunny.")))
    assert not none["ok"]


def test_estimate_uses_official_averages():
    summary = json.loads((compare.RESULTS / "matrix_summary.json").read_text())
    new = {"name": "new v2", "model": "x/new-model", "prompt_version": "v2"}
    e = compare.estimate([CUR, new], ["a", "b"], 3, summary)
    assert e["runs"] == 12
    mean = sum(t["avg_total_tokens"] for t in summary["totals"]) / 4
    assert e["tokens"] == round(2319.2 * 6 + mean * 6, -3)
    assert e["guessed"] == ["new v2"]


def test_jobs_are_interleaved():
    order = [(s["key"], sc, r) for s, sc, r in compare.jobs([CUR, CAND], ["a"], 2)]
    assert order == [("current", "a", 1), ("candidate_1", "a", 1),
                     ("current", "a", 2), ("candidate_1", "a", 2)]


def fake_run(errors):
    calls = []

    def run(model, scenario, prompt, client):
        calls.append(1)
        err = errors.pop(0) if errors else None
        return {"scenario": scenario, "summarizer": {"error": err, "summary": None, "tool_output": {}},
                "advisor": {"error": "upstream_failed", "advice": None}}
    return run, calls


def test_rate_limit_retries_then_succeeds():
    run, calls = fake_run(["api_error: RateLimitError: 429", None])
    waits = []
    out = compare.run_job(CUR, "snow", 1, None, {}, SETTINGS, run, waits.append)
    assert len(calls) == 2 and waits == [5] and out["rate_limit_retries"] == 1
    assert out["setup"] == "current" and "checks" in out


def test_rate_limit_gives_up_and_records_error():
    run, calls = fake_run(["api_error: RateLimitError: 429"] * 5)
    waits = []
    out = compare.run_job(CUR, "snow", 1, None, {}, SETTINGS, run, waits.append)
    assert len(calls) == 3 and waits == [5, 10]
    assert "RateLimitError" in out["summarizer"]["error"]


def test_run_comparison_yields_every_job():
    run, _ = fake_run([])
    out = list(compare.run_comparison([CUR, CAND], ["snow", "timeout"], 2, client=object(),
                                      settings=SETTINGS, run_fn=run))
    assert [d for d, _, _ in out] == list(range(1, 9)) and out[-1][1] == 8
    assert sorted(l["setup"] for _, _, l in out).count("current") == 4


def test_save_and_load_lab_run(tmp_path):
    path = compare.save_lab_run({"setups": [CUR]}, [{"a": 1}], tmp_path)
    assert path.name.startswith("lab_") and path.suffix == ".jsonl"
    assert compare.list_lab_runs(tmp_path) == [path]
    meta, lines = compare.load_lab_run(path)
    assert meta == {"setups": [CUR]} and lines == [{"a": 1}]
    with pytest.raises(FileExistsError):  # never overwrites
        path.open("x")
