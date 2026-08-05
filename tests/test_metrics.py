from judgewatch.metrics import compute_metrics


def test_metrics_exact_values():
    position = [
        # flip: canon differs between orders
        {"id": "p1", "verdict_ab": "A", "verdict_ba": "A", "canon_ab": "a", "canon_ba": "b", "errors": []},
        # stable
        {"id": "p2", "verdict_ab": "A", "verdict_ba": "B", "canon_ab": "a", "canon_ba": "a", "errors": []},
        # one side unparseable -> excluded from flip denominator
        {"id": "p3", "verdict_ab": None, "verdict_ba": "B", "canon_ab": None, "canon_ba": "a", "errors": ["parse_failure"]},
    ]
    bandwagon = [
        {"id": "p1", "clean": "a", "claimed_slot": "B", "verdict": "B", "canon": "b", "flipped": True, "errors": []},
        {"id": "p2", "clean": "a", "claimed_slot": "B", "verdict": "A", "canon": "a", "flipped": False, "errors": []},
        {"id": "p3", "skipped": True, "errors": []},
    ]
    verbosity = [
        {"id": "v1", "padded_pref": [True, False], "errors": []},
        {"id": "v2", "padded_pref": [True, True], "errors": []},
    ]
    consistency = [
        {"id": "c1", "scores": [7, 7, 7], "errors": []},
        {"id": "c2", "scores": [4, 6, 5], "errors": []},
        {"id": "c3", "scores": [8], "errors": ["parse_failure", "parse_failure"]},
    ]

    m = compute_metrics(position, bandwagon, verbosity, consistency, n_calls=20)

    assert m["position_flip_rate"] == 0.5          # 1 flip / 2 valid pairs
    assert m["first_slot_rate"] == 0.6             # 3 "A" of 5 parsed verdicts
    assert m["bandwagon_flip_rate"] == 0.5         # 1 flip / 2 valid
    assert m["verbosity_preference_rate"] == 0.75  # 3 padded wins / 4 judgments
    assert m["consistency_agreement_rate"] == 0.5  # c1 agrees, c2 does not, c3 excluded
    assert m["consistency_mean_range"] == 1.0      # (0 + 2) / 2
    assert m["failure_rate"] == 0.15               # 3 failures / 20 calls


def test_metrics_empty_inputs():
    m = compute_metrics([], [], [], [], n_calls=0)
    assert m["position_flip_rate"] is None
    assert m["verbosity_preference_rate"] is None
    assert m["consistency_mean_range"] is None
    assert m["failure_rate"] is None
