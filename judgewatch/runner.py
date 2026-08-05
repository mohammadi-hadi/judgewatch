"""Run the full probe battery against one or more judges and write results.

The frozen probe set ships inside the package, so an installed judgewatch
works standalone; data/ and docs/ output paths are relative to the working
directory (the repository root in the Makefile and CI).
"""

import json
import sys
from pathlib import Path

import yaml

from . import probes
from .clients import judge_from_spec
from .metrics import compute_metrics
from .probeset import load_probeset

DEFAULT_PROBESET = Path(__file__).resolve().parent / "probes" / "probeset_v1.yaml"


def _log(message):
    print(message, file=sys.stderr, flush=True)


def expected_calls(probeset, reps=3):
    return (
        2 * len(probeset.pairs)          # position: both orders
        + len(probeset.pairs)            # bandwagon: one injected order
        + 2 * len(probeset.verbosity)    # verbosity: both orders
        + reps * len(probeset.consistency)
    )


def run_judge(spec, probeset, reps=3, workers=1):
    judge = judge_from_spec(spec)
    label = spec.get("label", spec.get("model", "judge"))

    _log(f"{label}: position probe ({2 * len(probeset.pairs)} calls)")
    position = probes.run_position(judge, probeset.pairs, workers=workers)
    _log(f"{label}: bandwagon probe ({len(probeset.pairs)} calls)")
    bandwagon = probes.run_bandwagon(judge, probeset.pairs, position, workers=workers)
    _log(f"{label}: verbosity probe ({2 * len(probeset.verbosity)} calls)")
    verbosity = probes.run_verbosity(judge, probeset.verbosity, workers=workers)
    _log(f"{label}: consistency probe ({reps * len(probeset.consistency)} calls)")
    consistency = probes.run_consistency(judge, probeset.consistency, reps=reps, workers=workers)

    n_calls = expected_calls(probeset, reps)
    model = spec.get("model", judge.model)
    return {
        "judge": model,
        "label": spec.get("label", model),
        "provider": spec.get("provider", "anthropic"),
        "probeset": probeset.version,
        "n_calls": n_calls,
        "metrics": compute_metrics(position, bandwagon, verbosity, consistency, n_calls),
        "details": {
            "position": position,
            "bandwagon": bandwagon,
            "verbosity": verbosity,
            "consistency": consistency,
        },
    }


def parse_judge_arg(arg):
    """"provider:model" -> spec; a bare model name implies anthropic."""
    provider, _, model = arg.strip().partition(":")
    if not model:
        provider, model = "anthropic", provider
    return {"provider": provider, "model": model, "label": model}


def load_enabled_judges(path):
    data = yaml.safe_load(Path(path).read_text()) or {}
    return [j for j in data.get("judges", []) if j.get("enabled")]


def run(month, out_dir, judge_specs, probeset_path=DEFAULT_PROBESET, reps=3, workers=1):
    probeset = load_probeset(probeset_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for i, spec in enumerate(judge_specs, 1):
        _log(f"[{i}/{len(judge_specs)}] auditing {spec.get('label', spec.get('model'))}")
        result = run_judge(spec, probeset, reps=reps, workers=workers)
        result["run"] = month
        slug = result["judge"].replace("/", "-").replace(":", "-")
        (out / f"{slug}.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        _log(f"{result['label']}: {result['metrics']}")
    return results
