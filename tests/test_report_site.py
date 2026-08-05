import json

from judgewatch.report import build_latest
from judgewatch.sitegen import build_site


def fake_result(judge, label, flip):
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
            "verbosity_preference_rate": 0.6,
            "consistency_agreement_rate": 0.7,
            "consistency_mean_range": 0.4,
            "failure_rate": 0.0,
        },
        "details": {},
    }


def test_report_picks_latest_month_and_sorts(tmp_path):
    runs = tmp_path / "runs"
    old, new = runs / "2026-07", runs / "2026-08"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "x.json").write_text(json.dumps(fake_result("x", "Old", 0.9)))
    (new / "a.json").write_text(json.dumps(fake_result("a", "Worse", 0.4)))
    (new / "b.json").write_text(json.dumps(fake_result("b", "Better", 0.1)))

    payload = build_latest(runs, tmp_path / "latest.json")

    assert payload["run"] == "2026-08"
    assert [j["label"] for j in payload["judges"]] == ["Better", "Worse"]
    assert "details" not in payload["judges"][0]


def test_report_empty(tmp_path):
    payload = build_latest(tmp_path / "missing", tmp_path / "latest.json")
    assert payload == {"run": None, "judges": []}


def test_site_renders_judges(tmp_path):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"run": "2026-08", "judges": [
        {k: v for k, v in fake_result("a", "Judge <One>", 0.25).items() if k != "details"}
    ]}))
    out = build_site(latest, tmp_path / "docs")
    html = out.read_text()
    assert "Judge &lt;One&gt;" in html
    assert "25%" in html
    assert "<script src" not in html and "<link rel" not in html  # self-contained page
    assert (tmp_path / "docs" / ".nojekyll").exists()


def test_site_empty_state(tmp_path):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"run": None, "judges": []}))
    html = build_site(latest, tmp_path / "docs").read_text()
    assert "first monthly run is pending" in html
