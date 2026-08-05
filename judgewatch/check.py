"""CI gate: audit a judge and fail when bias metrics breach thresholds.

The default thresholds are starting points, not community norms — tune them to
your own risk tolerance with the --max-*/--min-* flags.
"""

import json
from pathlib import Path

from . import runner
from .probeset import load_probeset

# (metric key, CLI flag dest, kind, default limit)
THRESHOLDS = [
    ("position_flip_rate", "max_position_flip", "max", 0.25),
    ("verbosity_preference_rate", "max_verbosity_pref", "max", 0.65),
    ("bandwagon_flip_rate", "max_bandwagon_flip", "max", 0.25),
    ("consistency_agreement_rate", "min_consistency", "min", 0.60),
    ("failure_rate", "max_failures", "max", 0.05),
]


def evaluate(metrics, limits):
    """limits: {metric key: (kind, limit)} -> list of result rows."""
    rows = []
    for key, (kind, limit) in limits.items():
        value = metrics.get(key)
        if value is None:
            rows.append((key, kind, limit, None, False))
        else:
            ok = value <= limit if kind == "max" else value >= limit
            rows.append((key, kind, limit, value, ok))
    return rows


def run_check(specs, limits, probeset_path, reps=3, workers=1, save=None):
    """Audit each judge and print pass/FAIL per threshold. Returns overall ok."""
    probeset = load_probeset(probeset_path)
    all_ok = True
    results = []
    for spec in specs:
        result = runner.run_judge(spec, probeset, reps=reps, workers=workers)
        results.append(result)
        print(result["label"])
        for key, kind, limit, value, ok in evaluate(result["metrics"], limits):
            all_ok = all_ok and ok
            shown = "no data" if value is None else f"{value * 100:.0f}%"
            op = "<=" if kind == "max" else ">="
            verdict = "pass" if ok else "FAIL"
            print(f"  {key:<30} {shown:>8}  {op} {limit * 100:.0f}%   {verdict}")
    print("RESULT:", "pass" if all_ok else "FAIL")
    if save:
        Path(save).write_text(json.dumps(results, indent=2) + "\n")
    return all_ok
