"""CLI: judgewatch {run|check|report|site} (or python -m judgewatch).

Run from the repository root; paths are relative to it.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, check, report, runner, sitegen


def _resolve_specs(args, parser):
    if args.judges:
        return [runner.parse_judge_arg(a) for a in args.judges.split(",") if a.strip()]
    specs = runner.load_enabled_judges(args.judges_file)
    if not specs:
        parser.exit(
            1,
            "No judges enabled. Pass --judges provider:model or set "
            "enabled: true in judges.yaml.\n",
        )
    return specs


def main(argv=None):
    parser = argparse.ArgumentParser(prog="judgewatch")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--judges",
        help="Comma-separated provider:model list (e.g. anthropic:claude-haiku-4-5); "
        "overrides judges.yaml",
    )
    common.add_argument("--judges-file", default="judges.yaml")
    common.add_argument("--probeset", default=str(runner.DEFAULT_PROBESET))
    common.add_argument("--reps", type=int, default=3)
    common.add_argument(
        "--workers", type=int, default=4, help="Concurrent calls per probe (default 4)"
    )

    p_run = sub.add_parser(
        "run", parents=[common], help="Run the probe battery against judges"
    )
    p_run.add_argument("--month", default=datetime.now(timezone.utc).strftime("%Y-%m"))
    p_run.add_argument("--out", help="Output directory (default data/runs/<month>)")

    p_check = sub.add_parser(
        "check",
        parents=[common],
        help="Audit a judge and exit non-zero when bias thresholds are breached",
    )
    for _, dest, kind, default in check.THRESHOLDS:
        flag = "--" + dest.replace("_", "-")
        p_check.add_argument(
            flag,
            type=float,
            default=default,
            help=f"{kind} allowed value (default {default})",
        )
    p_check.add_argument("--save", help="Also write full per-item results to this file")

    sub.add_parser("report", help="Aggregate runs into data/latest.json")
    sub.add_parser("site", help="Render docs/ from data/latest.json")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        specs = _resolve_specs(args, parser)
        out = args.out or str(Path("data/runs") / args.month)
        runner.run(
            args.month,
            out,
            specs,
            probeset_path=args.probeset,
            reps=args.reps,
            workers=args.workers,
        )
    elif args.cmd == "check":
        specs = _resolve_specs(args, parser)
        limits = {
            key: (kind, getattr(args, dest)) for key, dest, kind, _ in check.THRESHOLDS
        }
        ok = check.run_check(
            specs,
            limits,
            probeset_path=args.probeset,
            reps=args.reps,
            workers=args.workers,
            save=args.save,
        )
        if not ok:
            raise SystemExit(1)
    elif args.cmd == "report":
        report.build_latest("data/runs", "data/latest.json")
    elif args.cmd == "site":
        sitegen.build_site("data/latest.json", "docs")


if __name__ == "__main__":
    main()
