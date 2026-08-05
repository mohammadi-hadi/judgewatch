"""Aggregate per-judge run files into data/latest.json for the site.

The payload carries the latest run plus the full month-by-month history, so
the site (and anyone consuming docs/data.json) can show change over time.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

SUMMARY_KEYS = ("judge", "label", "provider", "run", "probeset", "n_calls", "metrics")


def _summaries(month_dir):
    judges = [
        {k: data[k] for k in SUMMARY_KEYS}
        for f in sorted(month_dir.glob("*.json"))
        for data in [json.loads(f.read_text())]
    ]
    judges.sort(
        key=lambda j: (
            j["metrics"].get("position_flip_rate") is None,
            j["metrics"].get("position_flip_rate") or 0,
        )
    )
    return judges


def build_latest(runs_dir, latest_path):
    runs_dir = Path(runs_dir)
    months = (
        sorted(d for d in runs_dir.iterdir() if d.is_dir()) if runs_dir.exists() else []
    )
    history = [{"run": m.name, "judges": _summaries(m)} for m in months]
    payload = {
        "run": history[-1]["run"] if history else None,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "judges": history[-1]["judges"] if history else [],
        "history": history,
    }
    latest_path = Path(latest_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload
