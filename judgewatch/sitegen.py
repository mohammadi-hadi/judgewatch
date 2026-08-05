"""Render the static leaderboard (docs/) from data/latest.json.

Outputs are self-contained: inline CSS, no external requests, light/dark via
prefers-color-scheme plus a data-theme override. Alongside index.html, the
full payload is published as docs/data.json for machine consumption.
"""

import html
import json
from pathlib import Path

REPO_URL = "https://github.com/mohammadi-hadi/judgewatch"

# (metric key, panel title, note, reference line as a fraction or None)
METRIC_PANELS = [
    (
        "position_flip_rate",
        "Position flips",
        "Verdict changed when the two answers were swapped. Lower is better.",
        None,
    ),
    (
        "verbosity_preference_rate",
        "Verbosity preference",
        (
            "Chose the padded answer over the identical concise one. "
            "The dashed line marks 50% (indifferent); higher rewards length."
        ),
        0.5,
    ),
    (
        "bandwagon_flip_rate",
        "Bandwagon flips",
        (
            "A fabricated expert-consensus line flipped the judge's own verdict. "
            "Lower is better."
        ),
        None,
    ),
    (
        "consistency_agreement_rate",
        "Score agreement",
        (
            "Identical 1-10 scores across repeated runs of the same item. "
            "Higher is better."
        ),
        None,
    ),
]

TABLE_COLUMNS = [
    ("position_flip_rate", "Position flips"),
    ("first_slot_rate", "First-slot rate"),
    ("verbosity_preference_rate", "Verbosity pref."),
    ("bandwagon_flip_rate", "Bandwagon flips"),
    ("consistency_agreement_rate", "Score agreement"),
    ("failure_rate", "Failures"),
]


def _pct(value):
    return "–" if value is None else f"{value * 100:.0f}%"


def _panel(judges, key, title, note, ref):
    ref_marker = (
        f'<span class="ref" style="left:{ref * 100:.0f}%"></span>' if ref else ""
    )
    rows = []
    for judge in judges:
        value = judge["metrics"].get(key)
        width = 0.0 if value is None else max(0.0, min(1.0, value)) * 100
        label = html.escape(judge["label"])
        text = f"{label}: {_pct(value)}"
        rows.append(
            f'<div class="row" role="img" aria-label="{text}" title="{text}">'
            f'<span class="rlabel">{label}</span>'
            f'<span class="track">{ref_marker}'
            f'<span class="bar" style="width:{width:.1f}%"></span></span>'
            f'<span class="rval">{_pct(value)}</span>'
            f"</div>"
        )
    return (
        f'<section class="panel"><h3>{html.escape(title)}</h3>'
        f'<p class="note">{html.escape(note)}</p>'
        f'{"".join(rows)}</section>'
    )


def _delta(current, previous):
    if current is None or previous is None:
        return ""
    points = round((current - previous) * 100)
    if points == 0:
        return ""
    return f' <span class="delta">{points:+d}</span>'


def _table(judges, previous_metrics):
    head = "".join(f"<th>{html.escape(t)}</th>" for _, t in TABLE_COLUMNS)
    body = []
    for judge in judges:
        prev = previous_metrics.get(judge["judge"], {})
        cells = "".join(
            f'<td>{_pct(judge["metrics"].get(k))}'
            f'{_delta(judge["metrics"].get(k), prev.get(k))}</td>'
            for k, _ in TABLE_COLUMNS
        )
        body.append(
            f'<tr><td class="tlabel">{html.escape(judge["label"])}</td>{cells}</tr>'
        )
    return (
        f'<table><thead><tr><th>Judge</th>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )


def render(payload):
    judges = payload.get("judges", [])
    run = payload.get("run")
    history = payload.get("history") or []

    previous_metrics = {}
    if len(history) >= 2:
        previous_metrics = {
            j["judge"]: j["metrics"] for j in history[-2]["judges"]
        }

    if judges:
        status = (
            f'Audit <strong>{html.escape(str(run))}</strong> &middot; '
            f'{len(judges)} judge{"s" if len(judges) != 1 else ""} &middot; '
            f'probe set v{judges[0]["probeset"]} &middot; '
            f'{judges[0]["n_calls"]} calls per judge'
        )
        panels = "".join(_panel(judges, k, t, n, r) for k, t, n, r in METRIC_PANELS)
        delta_note = (
            '<p class="note">Small figures show the change vs the previous run, '
            "in percentage points.</p>"
            if previous_metrics
            else ""
        )
        content = (
            f'<div class="grid">{panels}</div>'
            f'<h2>All metrics</h2><div class="tablewrap">'
            f"{_table(judges, previous_metrics)}</div>{delta_note}"
        )
    else:
        status = "No audits published yet &mdash; the first monthly run is pending."
        content = (
            '<div class="empty">Results will appear here after the first audit. '
            f'Run one yourself: see the <a href="{REPO_URL}">repository</a>.</div>'
        )

    generated = payload.get("generated_at") or ""
    updated = (
        f" &middot; updated {html.escape(generated[:10])}" if judges and generated else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>judgewatch &mdash; monthly bias audits of LLM judges</title>
<meta name="description" content="Monthly bias audits of LLM judges: position, verbosity, bandwagon and consistency probes on a frozen probe set.">
<style>
  :root {{
    color-scheme: light;
    --page: #f9f9f7; --surface: #fcfcfb;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
    --accent: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --page: #0d0d0d; --surface: #1a1a19;
      --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
      --accent: #3987e5;
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
    --accent: #3987e5;
  }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    background: var(--page); color: var(--ink);
    font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 40px 20px 60px;
  }}
  main {{ max-width: 880px; margin: 0 auto; }}
  h1 {{ font-size: 26px; letter-spacing: -0.02em; }}
  h1 a {{ color: inherit; text-decoration: none; }}
  .tagline {{ color: var(--ink-2); margin: 4px 0 10px; }}
  .status {{ color: var(--muted); font-size: 13px; margin-bottom: 28px; }}
  h2 {{ font-size: 18px; margin: 36px 0 12px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }}
  .panel {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px;
  }}
  .panel h3 {{ font-size: 14px; }}
  .note {{ color: var(--muted); font-size: 12px; margin: 2px 0 12px; }}
  .row {{ display: flex; align-items: center; gap: 10px; margin: 7px 0; }}
  .rlabel {{ flex: 0 0 138px; font-size: 12.5px; color: var(--ink-2);
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .track {{ flex: 1; height: 14px; position: relative;
            border-left: 2px solid var(--grid); }}
  .ref {{ position: absolute; top: -2px; bottom: -2px;
          border-left: 1px dashed var(--muted); opacity: 0.6; }}
  .bar {{ display: block; height: 100%; background: var(--accent);
          border-radius: 0 4px 4px 0; min-width: 2px; }}
  .rval {{ flex: 0 0 44px; text-align: right; font-size: 12.5px; color: var(--ink);
           font-variant-numeric: tabular-nums; }}
  .tablewrap {{ overflow-x: auto; background: var(--surface);
                border: 1px solid var(--border); border-radius: 10px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: right; padding: 9px 14px; border-bottom: 1px solid var(--grid);
            font-variant-numeric: tabular-nums; white-space: nowrap; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ color: var(--muted); font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  .tlabel {{ color: var(--ink); }}
  .delta {{ color: var(--muted); font-size: 11px; }}
  .empty {{
    background: var(--surface); border: 1px dashed var(--grid); border-radius: 10px;
    padding: 40px 24px; text-align: center; color: var(--ink-2);
  }}
  .method {{ color: var(--ink-2); }}
  .method li {{ margin: 6px 0 6px 18px; }}
  a {{ color: var(--accent); }}
  footer {{ margin-top: 44px; color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
  <h1><a href="{REPO_URL}">judgewatch</a></h1>
  <p class="tagline">Monthly bias audits of LLM judges: the same frozen probe set, every month, so drift and bias are visible.</p>
  <p class="status">{status}{updated}</p>
  {content}
  <h2>Method</h2>
  <ul class="method">
    <li><strong>Position</strong>: every answer pair is judged in both orders; a flip means position, not content, decided.</li>
    <li><strong>Verbosity</strong>: a concise correct answer vs the same answer wrapped in filler, shown in both orders.</li>
    <li><strong>Bandwagon</strong>: a fabricated "9 out of 10 experts prefer&hellip;" line targets the judge's own clean verdict.</li>
    <li><strong>Consistency</strong>: the same answer scored repeatedly; disagreement with itself is noise, not judgment.</li>
    <li>The probe set is frozen (v1); judges run with provider-default settings; parse failures are reported, not hidden.</li>
  </ul>
  <footer>
    <a href="{REPO_URL}">Source &amp; methodology</a> &middot;
    <a href="data.json">Data (JSON)</a> &middot;
    <a href="{REPO_URL}#sponsoring">Sponsor the audit</a> &middot; MIT licensed
  </footer>
</main>
</body>
</html>
"""


def build_site(latest_path, docs_dir):
    payload = json.loads(Path(latest_path).read_text())
    docs = Path(docs_dir)
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "index.html").write_text(render(payload))
    (docs / "data.json").write_text(json.dumps(payload, indent=2) + "\n")
    (docs / ".nojekyll").write_text("")
    return docs / "index.html"
