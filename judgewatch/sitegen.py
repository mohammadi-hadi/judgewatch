"""Render the static leaderboard (docs/) from data/latest.json.

Outputs are self-contained: inline CSS/SVG, no external requests, light/dark
via prefers-color-scheme plus a data-theme override. Alongside index.html the
generator publishes docs/data.json (the full payload) and docs/badges/*.json
(shields.io endpoint format).
"""

import html
import json
from pathlib import Path

REPO_URL = "https://github.com/mohammadi-hadi/judgewatch"
SITE_URL = "https://mohammadi.cv/judgewatch/"
TAGLINE = (
    "Monthly bias audits of LLM judges: the same frozen probe set, "
    "every month, so drift and bias are visible."
)

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

# Metrics where the ideal is 50% rather than an extreme.
CENTERED_METRICS = {"verbosity_preference_rate", "first_slot_rate"}
HIGHER_IS_BETTER = {"consistency_agreement_rate"}


def _pct(value):
    return "–" if value is None else f"{value * 100:.0f}%"


def _slug(judge_id):
    return judge_id.replace("/", "-").replace(":", "-")


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


def _delta_class(key, current, previous):
    if key in CENTERED_METRICS:
        improved = abs(current - 0.5) < abs(previous - 0.5)
        worsened = abs(current - 0.5) > abs(previous - 0.5)
    elif key in HIGHER_IS_BETTER:
        improved, worsened = current > previous, current < previous
    else:
        improved, worsened = current < previous, current > previous
    return " good" if improved else " bad" if worsened else ""


def _delta(key, current, previous):
    if current is None or previous is None:
        return ""
    points = round((current - previous) * 100)
    if points == 0:
        return ""
    cls = _delta_class(key, current, previous)
    return f' <span class="delta{cls}">{points:+d}</span>'


def _series(history, judge_id, key="position_flip_rate"):
    points = []
    for month in history:
        for judge in month["judges"]:
            if judge["judge"] == judge_id:
                value = judge["metrics"].get(key)
                if value is not None:
                    points.append((month["run"], value))
    return points


def _sparkline(points):
    width, height, pad = 96, 24, 3
    n = len(points)
    xs = [pad + i * (width - 2 * pad) / (n - 1) for i in range(n)]
    ys = [height - pad - v * (height - 2 * pad) for _, v in points]
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{ys[i]:.1f}" for i in range(n)
    )
    title = html.escape(
        "position flips: " + ", ".join(f"{run} {v * 100:.0f}%" for run, v in points)
    )
    return (
        f'<svg class="spark" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<path d="{path}" fill="none" stroke="var(--accent)" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3" fill="var(--accent)"/>'
        f"</svg>"
    )


def _table(judges, previous_metrics, history):
    sparks = {
        j["judge"]: points
        for j in judges
        if len(points := _series(history, j["judge"])) >= 2
    }
    head = "".join(f"<th>{html.escape(t)}</th>" for _, t in TABLE_COLUMNS)
    trend_head = "<th>Trend</th>" if sparks else ""
    body = []
    for judge in judges:
        prev = previous_metrics.get(judge["judge"], {})
        cells = "".join(
            f'<td>{_pct(judge["metrics"].get(k))}'
            f'{_delta(k, judge["metrics"].get(k), prev.get(k))}</td>'
            for k, _ in TABLE_COLUMNS
        )
        trend = ""
        if sparks:
            spark = _sparkline(sparks[judge["judge"]]) if judge["judge"] in sparks else "–"
            trend = f'<td class="trend">{spark}</td>'
        body.append(
            f'<tr><td class="tlabel">{html.escape(judge["label"])}</td>'
            f"{trend}{cells}</tr>"
        )
    return (
        f'<table><thead><tr><th>Judge</th>{trend_head}{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )


def render(payload):
    judges = payload.get("judges", [])
    run = payload.get("run")
    history = payload.get("history") or []

    previous_metrics = {}
    if len(history) >= 2:
        previous_metrics = {j["judge"]: j["metrics"] for j in history[-2]["judges"]}

    if judges:
        status = (
            f'Audit <strong>{html.escape(str(run))}</strong> &middot; '
            f'{len(judges)} judge{"s" if len(judges) != 1 else ""} &middot; '
            f'probe set v{judges[0]["probeset"]} &middot; '
            f'{judges[0]["n_calls"]} calls per judge'
        )
        panels = "".join(_panel(judges, k, t, n, r) for k, t, n, r in METRIC_PANELS)
        delta_note = (
            '<p class="note">Small figures show the change vs the previous run in '
            "percentage points; green moved the right way, red the wrong way "
            "(for verbosity and first-slot, the right way is toward 50%). "
            "The trend line tracks position flips across runs.</p>"
            if previous_metrics
            else ""
        )
        content = (
            f'<div class="grid">{panels}</div>'
            f'<h2>All metrics</h2><div class="tablewrap">'
            f"{_table(judges, previous_metrics, history)}</div>{delta_note}"
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
<meta name="description" content="{TAGLINE}">
<meta property="og:title" content="judgewatch — monthly bias audits of LLM judges">
<meta property="og:description" content="{TAGLINE}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<style>
  :root {{
    color-scheme: light;
    --page: #f9f9f7; --surface: #fcfcfb;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
    --accent: #2a78d6; --delta-good: #006300; --delta-bad: #d03b3b;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --page: #0d0d0d; --surface: #1a1a19;
      --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
      --accent: #3987e5; --delta-good: #0ca30c; --delta-bad: #e66767;
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
    --accent: #3987e5; --delta-good: #0ca30c; --delta-bad: #e66767;
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
  .trend {{ line-height: 0; }}
  .spark {{ display: inline-block; vertical-align: middle; }}
  .delta {{ color: var(--muted); font-size: 11px; }}
  .delta.good {{ color: var(--delta-good); }}
  .delta.bad {{ color: var(--delta-bad); }}
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
  <p class="tagline">{TAGLINE}</p>
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


def _write_badges(payload, docs):
    badges = docs / "badges"
    badges.mkdir(exist_ok=True)
    judges = payload.get("judges", [])
    if judges:
        top = judges[0]
        leader = {
            "schemaVersion": 1,
            "label": "judgewatch",
            "message": (
                f'{top["label"]}: {_pct(top["metrics"].get("position_flip_rate"))} '
                "position flips"
            ),
            "color": "2a78d6",
        }
    else:
        leader = {
            "schemaVersion": 1,
            "label": "judgewatch",
            "message": "no audits yet",
            "color": "9f9f9f",
        }
    (badges / "leader.json").write_text(json.dumps(leader) + "\n")
    for judge in judges:
        badge = {
            "schemaVersion": 1,
            "label": "judgewatch",
            "message": (
                f'{_pct(judge["metrics"].get("position_flip_rate"))} position flips'
            ),
            "color": "2a78d6",
        }
        (badges / f"{_slug(judge['judge'])}.json").write_text(json.dumps(badge) + "\n")


def build_site(latest_path, docs_dir):
    payload = json.loads(Path(latest_path).read_text())
    docs = Path(docs_dir)
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "index.html").write_text(render(payload))
    (docs / "data.json").write_text(json.dumps(payload, indent=2) + "\n")
    _write_badges(payload, docs)
    (docs / ".nojekyll").write_text("")
    return docs / "index.html"
