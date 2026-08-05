from pathlib import Path

import pytest

from judgewatch.__main__ import main
from judgewatch.check import evaluate

PROBESET = str(Path(__file__).resolve().parent.parent / "probes" / "probeset_v1.yaml")


def test_evaluate_kinds_and_missing_data():
    limits = {
        "position_flip_rate": ("max", 0.25),
        "consistency_agreement_rate": ("min", 0.6),
        "bandwagon_flip_rate": ("max", 0.25),
    }
    metrics = {
        "position_flip_rate": 0.1,
        "consistency_agreement_rate": 0.5,
        "bandwagon_flip_rate": None,
    }
    rows = {key: ok for key, _, _, _, ok in evaluate(metrics, limits)}
    assert rows["position_flip_rate"] is True
    assert rows["consistency_agreement_rate"] is False
    assert rows["bandwagon_flip_rate"] is False  # no data counts as a failure


def test_check_fails_on_default_thresholds(capsys):
    # The mock judge's position flip rate (62%) breaches the 25% default.
    with pytest.raises(SystemExit) as excinfo:
        main(["check", "--judges", "mock:mock-judge", "--probeset", PROBESET, "--workers", "1"])
    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert "FAIL" in out


def test_check_passes_with_loose_thresholds(capsys):
    main(
        [
            "check",
            "--judges", "mock:mock-judge",
            "--probeset", PROBESET,
            "--workers", "1",
            "--max-position-flip", "1",
            "--max-verbosity-pref", "1",
            "--max-bandwagon-flip", "1",
            "--min-consistency", "0",
            "--max-failures", "1",
        ]
    )
    out = capsys.readouterr().out
    assert "RESULT: pass" in out
