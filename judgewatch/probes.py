"""The four probes. Each returns per-item records; metrics.py aggregates them.

Canonical labels: "a" and "b" always refer to the original answers in the probe
set, regardless of the order they were shown in. A slot letter ("A"/"B") refers
to presentation position within one prompt.

Probes accept a `workers` count and fan calls out across items with a thread
pool; results keep item order either way.
"""

from concurrent.futures import ThreadPoolExecutor

from .clients import JudgeError
from .prompts import build_pairwise, build_score, pad_answer, parse_score, parse_verdict


def _map(fn, items, workers):
    if workers and workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(fn, items))
    return [fn(item) for item in items]


def _ask_pairwise(judge, question, first, second, claimed_side=None):
    try:
        text = judge.complete(build_pairwise(question, first, second, claimed_side))
    except JudgeError as exc:
        return None, f"error: {exc}"
    verdict = parse_verdict(text)
    return verdict, None if verdict else "parse_failure"


def run_position(judge, pairs, workers=1):
    """Judge every pair in both presentation orders."""

    def probe_one(pair):
        v_ab, err_ab = _ask_pairwise(judge, pair.question, pair.answer_a, pair.answer_b)
        v_ba, err_ba = _ask_pairwise(judge, pair.question, pair.answer_b, pair.answer_a)
        return {
            "id": pair.id,
            "verdict_ab": v_ab,
            "verdict_ba": v_ba,
            "canon_ab": {"A": "a", "B": "b"}.get(v_ab),
            "canon_ba": {"A": "b", "B": "a"}.get(v_ba),
            "errors": [e for e in (err_ab, err_ba) if e],
        }

    return _map(probe_one, pairs, workers)


def run_bandwagon(judge, pairs, position_records, workers=1):
    """Re-judge each pair with a fabricated consensus favoring the clean loser.

    The baseline is the A-first verdict from the position probe, so the claim
    always pushes against the judge's own prior decision.
    """
    baseline = {r["id"]: r for r in position_records}

    def probe_one(pair):
        clean = baseline[pair.id]["canon_ab"]
        if clean is None:
            return {"id": pair.id, "skipped": True, "errors": []}
        claimed_slot = "B" if clean == "a" else "A"
        verdict, err = _ask_pairwise(
            judge, pair.question, pair.answer_a, pair.answer_b, claimed_side=claimed_slot
        )
        canon = {"A": "a", "B": "b"}.get(verdict)
        return {
            "id": pair.id,
            "clean": clean,
            "claimed_slot": claimed_slot,
            "verdict": verdict,
            "canon": canon,
            "flipped": canon is not None and canon != clean,
            "errors": [err] if err else [],
        }

    return _map(probe_one, pairs, workers)


def run_verbosity(judge, items, workers=1):
    """Concise answer vs the same answer wrapped in filler, judged in both orders."""

    def probe_one(item):
        padded = pad_answer(item.answer)
        v1, e1 = _ask_pairwise(judge, item.question, item.answer, padded)
        v2, e2 = _ask_pairwise(judge, item.question, padded, item.answer)
        padded_won_first = {"A": False, "B": True}.get(v1)
        padded_won_second = {"A": True, "B": False}.get(v2)
        return {
            "id": item.id,
            "padded_pref": [
                x for x in (padded_won_first, padded_won_second) if x is not None
            ],
            "errors": [e for e in (e1, e2) if e],
        }

    return _map(probe_one, items, workers)


def run_consistency(judge, items, reps=3, workers=1):
    """Score the same answer several times; measure agreement."""

    def probe_one(item):
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
        return {"id": item.id, "scores": scores, "errors": errors}

    return _map(probe_one, items, workers)
