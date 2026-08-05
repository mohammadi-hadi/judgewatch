"""Loading of the frozen probe set."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Pair:
    id: str
    question: str
    answer_a: str
    answer_b: str


@dataclass(frozen=True)
class VerbosityItem:
    id: str
    question: str
    answer: str


@dataclass(frozen=True)
class ConsistencyItem:
    id: str
    question: str
    answer: str


@dataclass(frozen=True)
class ProbeSet:
    version: int
    pairs: list[Pair]
    verbosity: list[VerbosityItem]
    consistency: list[ConsistencyItem]


def load_probeset(path: str | Path) -> ProbeSet:
    data = yaml.safe_load(Path(path).read_text())
    return ProbeSet(
        version=data["version"],
        pairs=[Pair(**p) for p in data["pairs"]],
        verbosity=[VerbosityItem(**v) for v in data["verbosity"]],
        consistency=[ConsistencyItem(**c) for c in data["consistency"]],
    )
