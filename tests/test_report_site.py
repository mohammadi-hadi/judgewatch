import json

from judgewatch.report import build_latest
from judgewatch.sitegen import build_site


def fake_result(judge, label, flip, verbosity=0.6):
    return {
        "judge": judge,
        "label": label,
        "provider": "anthropic",
        "run": "2026-08",
        "probeset": 1,
        "n_calls": 96,
        "metrics": {
            "position_flip_rate": flip,
            "first_slot_rate": 0.55,
            "bandwagon_flip_rate": 0.2,
            "verbosity_preference_rate": verbosity,
            "consistency_agreement_rate": 0.7,
            "consistency_mean_range": 0.4,
            "failure_rate": 0.0,
        },
        "details": {},
    }


def test_report_history_and_sorting(tmp_path):
    runs = tmp_path / "runs"
    old, new = runs / "2026-07", runs / "2026-08"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "a.json").write_text(json.dumps(fake_result("a", "A", 0.4)))
    (new / "a.json").write_text(json.dumps(fake_result("a", "Worse", 0.4)))
    (new / "b.json").write_text(json.dumps(fake_result("b", "Better", 0.1)))

    payload = build_latest(runs, tmp_path / "latest.json")

    assert payload["run"] == "2026-08"
    assert [j["label"] for j in payload["judges"]] == ["Better", "Worse"]
    assert "details" not in payload["judges"][0]
    assert [h["run"] for h in payload["history"]] == ["2026-07", "2026-08"]
    assert payload["generated_at"]


def test_report_empty(tmp_path):
    payload = build_latest(tmp_path / "missing", tmp_path / "latest.json")
    assert payload["run"] is None
    assert payload["judges"] == []
    assert payload["history"] == []


def test_site_renders_judges_with_deltas(tmp_path):
    prev = {k: v for k, v in fake_result("a", "Judge <One>", 0.40).items() if k != "details"}
    curr = {k: v for k, v in fake_result("a", "Judge <One>", 0.25).items() if k != "details"}
    latest = tmp_path / "latest.json"
    latest.write_text(
        json.dumps(
            {
                "run": "2026-08",
                "generated_at": "2026-08-05T10:00:00+00:00",
                "judges": [curr],
                "history": [
                    {"run": "2026-07", "judges": [prev]},
                    {"run": "2026-08", "judges": [curr]},
                ],
            }
        )
    )

    out = build_site(latest, tmp_path / "docs")
    html = out.read_text()

    assert "Judge &lt;One&gt;" in html
    assert "25%" in html
    assert '<span class="delta">-15</span>' in html      # position flips 40% -> 25%
    assert 'class="ref"' in html                          # 50% chance line on verbosity
    assert "updated 2026-08-05" in html
    assert "<script src" not in html and "<link rel" not in html  # self-contained
    assert (tmp_path / "docs" / ".nojekyll").exists()
    assert json.loads((tmp_path / "docs" / "data.json").read_text())["run"] == "2026-08"


def test_site_single_run_has_no_deltas(tmp_path):
    curr = {k: v for k, v in fake_result("a", "Solo", 0.25).items() if k != "details"}
    latest = tmp_path / "latest.json"
    latest.write_text(
        json.dumps(
            {
                "run": "2026-08",
                "generated_at": "2026-08-05T10:00:00+00:00",
                "judges": [curr],
                "history": [{"run": "2026-08", "judges": [curr]}],
            }
        )
    )
    html = build_site(latest, tmp_path / "docs").read_text()
    assert 'class="delta"' not in html


def test_site_empty_state(tmp_path):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"run": None, "judges": [], "history": []}))
    html = build_site(latest, tmp_path / "docs").read_text()
    assert "first monthly run is pending" in html
