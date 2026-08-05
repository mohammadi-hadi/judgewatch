"""Aggregate per-judge run files into data/latest.json for the site."""

import json
from pathlib import Path

SUMMARY_KEYS = ("judge", "label", "provider", "run", "probeset", "n_calls", "metrics")


def build_latest(runs_dir, latest_path):
    runs_dir = Path(runs_dir)
    months = (
        sorted(d for d in runs_dir.iterdir() if d.is_dir()) if runs_dir.exists() else []
    )
    if not months:
        payload = {"run": None, "judges": []}
    else:
        latest = months[-1]
        judges = [
            {k: data[k] for k in SUMMARY_KEYS}
            for f in sorted(latest.glob("*.json"))
            for data in [json.loads(f.read_text())]
        ]
        judges.sort(
            key=lambda j: (
                j["metrics"].get("position_flip_rate") is None,
                j["metrics"].get("position_flip_rate") or 0,
            )
        )
        payload = {"run": latest.name, "judges": judges}
    latest_path = Path(latest_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload
