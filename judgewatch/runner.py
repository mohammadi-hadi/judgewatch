"""Run the full probe battery against one or more judges and write results.

All paths are relative to the repository root — run commands from there
(the Makefile and CI both do).
"""

import json
from pathlib import Path

import yaml

from . import probes
from .clients import judge_from_spec
from .metrics import compute_metrics
from .probeset import load_probeset

DEFAULT_PROBESET = Path("probes/probeset_v1.yaml")


def expected_calls(probeset, reps=3):
    return (
        2 * len(probeset.pairs)          # position: both orders
        + len(probeset.pairs)            # bandwagon: one injected order
        + 2 * len(probeset.verbosity)    # verbosity: both orders
        + reps * len(probeset.consistency)
    )


def run_judge(spec, probeset, reps=3):
    judge = judge_from_spec(spec)
    position = probes.run_position(judge, probeset.pairs)
    bandwagon = probes.run_bandwagon(judge, probeset.pairs, position)
    verbosity = probes.run_verbosity(judge, probeset.verbosity)
    consistency = probes.run_consistency(judge, probeset.consistency, reps=reps)
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


def run(month, out_dir, judge_specs, probeset_path=DEFAULT_PROBESET, reps=3):
    probeset = load_probeset(probeset_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for spec in judge_specs:
        result = run_judge(spec, probeset, reps=reps)
        result["run"] = month
        slug = result["judge"].replace("/", "-").replace(":", "-")
        (out / f"{slug}.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        print(f"audited {result['label']}: {result['metrics']}")
    return results
