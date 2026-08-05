# Contributing

## Setup

```
make install
make lint
make test
```

Tests run entirely offline against a deterministic mock judge — no API keys
needed. CI runs the same lint + tests on Python 3.10 and 3.14.

## Adding a judge

Open a PR adding an entry to `judges.yaml` (keep `enabled: false`; the
maintainer enables judges that the monthly budget covers). Any
Anthropic model or OpenAI-compatible `/chat/completions` endpoint works.

## Probe items

The current probe set is frozen — items in
`judgewatch/probes/probeset_v1.yaml` must not change, or months stop being
comparable. Propose new items for a future `probeset_v2.yaml`. Criteria:

- **Pairs**: both answers self-contained and plausible. Close-call pairs must
  be genuinely defensible on both sides; clear-gap pairs must contain one
  real, checkable error.
- **Verbosity items**: the concise answer must be complete and correct, so the
  padded variant adds nothing but words.
- **Consistency items**: vary quality deliberately, from excellent to subtly
  or badly wrong.

## Results are generated, never edited

Everything under `data/` and `docs/` is produced by `python -m judgewatch`.
Don't hand-edit those files in a PR; fix the generator instead.
