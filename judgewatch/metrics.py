"""Aggregate per-item probe records into headline metrics.

Failed or unparseable calls are excluded from each metric's denominator and
reported separately as failure_rate — failures are a finding, not noise.
"""


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def compute_metrics(position, bandwagon, verbosity, consistency, n_calls):
    valid_position = [r for r in position if r["canon_ab"] and r["canon_ba"]]
    flips = sum(1 for r in valid_position if r["canon_ab"] != r["canon_ba"])
    slot_choices = [
        v for r in position for v in (r["verdict_ab"], r["verdict_ba"]) if v
    ]

    valid_bandwagon = [
        r for r in bandwagon if not r.get("skipped") and r.get("canon") is not None
    ]
    bandwagon_flips = sum(1 for r in valid_bandwagon if r["flipped"])

    verbosity_judgments = [x for r in verbosity for x in r["padded_pref"]]

    scored = [r for r in consistency if len(r["scores"]) >= 2]
    full_agreement = sum(1 for r in scored if len(set(r["scores"])) == 1)
    ranges = [max(r["scores"]) - min(r["scores"]) for r in scored]

    failures = sum(
        len(r.get("errors", []))
        for group in (position, bandwagon, verbosity, consistency)
        for r in group
    )

    return {
        "position_flip_rate": _rate(flips, len(valid_position)),
        "first_slot_rate": _rate(
            sum(1 for v in slot_choices if v == "A"), len(slot_choices)
        ),
        "bandwagon_flip_rate": _rate(bandwagon_flips, len(valid_bandwagon)),
        "verbosity_preference_rate": _rate(
            sum(verbosity_judgments), len(verbosity_judgments)
        ),
        "consistency_agreement_rate": _rate(full_agreement, len(scored)),
        "consistency_mean_range": (
            round(sum(ranges) / len(ranges), 4) if ranges else None
        ),
        "failure_rate": _rate(failures, n_calls),
    }
