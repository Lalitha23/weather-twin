"""run_matrix writes scratch files by default and guards the official ones."""
import json
import shutil
import sys

import pytest

import runner.run_matrix as rm

OFFICIAL_RUNS = rm.RESULTS / "official_matrix_oct25.jsonl"


@pytest.fixture
def results(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, "RESULTS", tmp_path)
    return tmp_path


def run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["run_matrix", *args])
    rm.main()


def fake_run_one(model, scenario, prompt, client):
    return {"scenario": scenario, "model": model, "prompt_version": prompt,
            "summarizer": {"summary": None, "tool_output": {}, "error": "no_tool_call",
                           "usage": {"total_tokens": 10}, "latency_s": 1.0},
            "advisor": {"advice": None, "error": "upstream_failed",
                        "usage": {"total_tokens": 0}, "latency_s": None}}


def test_default_run_writes_scratch_only(results, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test")
    monkeypatch.setattr(rm, "run_one", fake_run_one)
    monkeypatch.setattr(rm, "make_client", lambda: None)
    run_main(monkeypatch, "--models", "x/model", "--prompts", "v2", "--scenarios", "snow", "--repeats", "1")
    assert sorted(p.name for p in results.iterdir()) == ["matrix_scratch.jsonl",
                                                         "matrix_scratch_summary.json"]


def test_default_rescore_reads_and_writes_scratch(results, monkeypatch):
    lines = OFFICIAL_RUNS.read_text().splitlines()[:3]
    (results / "matrix_scratch.jsonl").write_text("\n".join(lines) + "\n")
    run_main(monkeypatch, "--rescore")
    summary = json.loads((results / "matrix_scratch_summary.json").read_text())
    assert summary["totals"][0]["runs"] == 3
    assert not (results / "official_matrix_oct25.jsonl").exists()
    assert not (results / "matrix_summary.json").exists()


def test_official_refuses_when_official_run_exists(results, monkeypatch):
    shutil.copy(OFFICIAL_RUNS, results / OFFICIAL_RUNS.name)
    before = (results / OFFICIAL_RUNS.name).read_bytes()
    with pytest.raises(SystemExit, match="already exists"):
        run_main(monkeypatch, "--rescore", "--official")
    assert (results / OFFICIAL_RUNS.name).read_bytes() == before
    assert not (results / "matrix_summary.json").exists()


def test_official_force_rescores_official_files(results, monkeypatch):
    shutil.copy(OFFICIAL_RUNS, results / OFFICIAL_RUNS.name)
    run_main(monkeypatch, "--rescore", "--official", "--force")
    summary = json.loads((results / "matrix_summary.json").read_text())
    committed = json.loads((OFFICIAL_RUNS.parent / "matrix_summary.json").read_text())
    assert sum(t["runs"] for t in summary["totals"]) == 132
    assert [t["checks"] for t in summary["totals"]] == [t["checks"] for t in committed["totals"]]
