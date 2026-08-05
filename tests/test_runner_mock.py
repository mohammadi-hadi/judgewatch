import json
from pathlib import Path

from judgewatch import runner
from judgewatch.probeset import load_probeset

PROBESET = Path(__file__).resolve().parent.parent / "probes" / "probeset_v1.yaml"


def test_probeset_loads_and_counts():
    ps = load_probeset(PROBESET)
    assert ps.version == 1
    assert len(ps.pairs) == 16
    assert len(ps.verbosity) == 12
    assert len(ps.consistency) == 8
    assert runner.expected_calls(ps, reps=3) == 96


def test_mock_end_to_end(tmp_path):
    results = runner.run(
        month="2026-01",
        out_dir=tmp_path,
        judge_specs=[{"provider": "mock", "model": "mock-judge", "label": "Mock"}],
        probeset_path=PROBESET,
    )
    assert len(results) == 1
    result = results[0]
    assert result["n_calls"] == 96
    assert result["run"] == "2026-01"

    metrics = result["metrics"]
    for key in ("position_flip_rate", "verbosity_preference_rate", "bandwagon_flip_rate"):
        assert metrics[key] is not None
        assert 0.0 <= metrics[key] <= 1.0
    assert metrics["failure_rate"] == 0.0

    written = json.loads((tmp_path / "mock-judge.json").read_text())
    assert written["metrics"] == metrics
    assert set(written["details"]) == {"position", "bandwagon", "verbosity", "consistency"}


def test_workers_do_not_change_results(tmp_path):
    spec = [{"provider": "mock", "model": "mock-judge", "label": "Mock"}]
    serial = runner.run("2026-01", tmp_path / "s", spec, probeset_path=PROBESET, workers=1)
    threaded = runner.run("2026-01", tmp_path / "t", spec, probeset_path=PROBESET, workers=4)
    assert serial[0]["metrics"] == threaded[0]["metrics"]
    assert serial[0]["details"] == threaded[0]["details"]


def test_parse_judge_arg():
    assert runner.parse_judge_arg("anthropic:claude-haiku-4-5")["model"] == "claude-haiku-4-5"
    assert runner.parse_judge_arg("claude-haiku-4-5")["provider"] == "anthropic"
    spec = runner.parse_judge_arg("openai-compatible:some/model")
    assert spec["provider"] == "openai-compatible"
    assert spec["model"] == "some/model"
