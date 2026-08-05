"""The four probes. Each returns per-item records; metrics.py aggregates them.

Canonical labels: "a" and "b" always refer to the original answers in the probe
set, regardless of the order they were shown in. A slot letter ("A"/"B") refers
to presentation position within one prompt.
"""

from .clients import JudgeError
from .prompts import build_pairwise, build_score, pad_answer, parse_score, parse_verdict


def _ask_pairwise(judge, question, first, second, claimed_side=None):
    try:
        text = judge.complete(build_pairwise(question, first, second, claimed_side))
    except JudgeError as exc:
        return None, f"error: {exc}"
    verdict = parse_verdict(text)
    return verdict, None if verdict else "parse_failure"


def run_position(judge, pairs):
    """Judge every pair in both presentation orders."""
    records = []
    for pair in pairs:
        v_ab, err_ab = _ask_pairwise(judge, pair.question, pair.answer_a, pair.answer_b)
        v_ba, err_ba = _ask_pairwise(judge, pair.question, pair.answer_b, pair.answer_a)
        records.append(
            {
                "id": pair.id,
                "verdict_ab": v_ab,
                "verdict_ba": v_ba,
                "canon_ab": {"A": "a", "B": "b"}.get(v_ab),
                "canon_ba": {"A": "b", "B": "a"}.get(v_ba),
                "errors": [e for e in (err_ab, err_ba) if e],
            }
        )
    return records


def run_bandwagon(judge, pairs, position_records):
    """Re-judge each pair with a fabricated consensus favoring the clean loser.

    The baseline is the A-first verdict from the position probe, so the claim
    always pushes against the judge's own prior decision.
    """
    baseline = {r["id"]: r for r in position_records}
    records = []
    for pair in pairs:
        clean = baseline[pair.id]["canon_ab"]
        if clean is None:
            records.append({"id": pair.id, "skipped": True, "errors": []})
            continue
        claimed_slot = "B" if clean == "a" else "A"
        verdict, err = _ask_pairwise(
            judge, pair.question, pair.answer_a, pair.answer_b, claimed_side=claimed_slot
        )
        canon = {"A": "a", "B": "b"}.get(verdict)
        records.append(
            {
                "id": pair.id,
                "clean": clean,
                "claimed_slot": claimed_slot,
                "verdict": verdict,
                "canon": canon,
                "flipped": canon is not None and canon != clean,
                "errors": [err] if err else [],
            }
        )
    return records


def run_verbosity(judge, items):
    """Concise answer vs the same answer wrapped in filler, judged in both orders."""
    records = []
    for item in items:
        padded = pad_answer(item.answer)
        v1, e1 = _ask_pairwise(judge, item.question, item.answer, padded)
        v2, e2 = _ask_pairwise(judge, item.question, padded, item.answer)
        padded_won_first = {"A": False, "B": True}.get(v1)
        padded_won_second = {"A": True, "B": False}.get(v2)
        records.append(
            {
                "id": item.id,
                "padded_pref": [
                    x for x in (padded_won_first, padded_won_second) if x is not None
                ],
                "errors": [e for e in (e1, e2) if e],
            }
        )
    return records


def run_consistency(judge, items, reps=3):
    """Score the same answer several times; measure agreement."""
    records = []
    for item in items:
        scores, errors = [], []
        for _ in range(reps):
            try:
                text = judge.complete(build_score(item.question, item.answer))
            except JudgeError as exc:
                errors.append(f"error: {exc}")
                continue
            score = parse_score(text)
            if score is None:
                errors.append("parse_failure")
            else:
                scores.append(score)
        records.append({"id": item.id, "scores": scores, "errors": errors})
    return records
