"""CLI: judgewatch {run|report|site} (or python -m judgewatch).

Run from the repository root; paths are relative to it.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from . import report, runner, sitegen


def main(argv=None):
    parser = argparse.ArgumentParser(prog="judgewatch")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run the probe battery against judges")
    p_run.add_argument(
        "--month", default=datetime.now(timezone.utc).strftime("%Y-%m")
    )
    p_run.add_argument(
        "--judges",
        help="Comma-separated provider:model list (e.g. anthropic:claude-haiku-4-5); "
        "overrides judges.yaml",
    )
    p_run.add_argument("--judges-file", default="judges.yaml")
    p_run.add_argument("--probeset", default=str(runner.DEFAULT_PROBESET))
    p_run.add_argument("--out", help="Output directory (default data/runs/<month>)")
    p_run.add_argument("--reps", type=int, default=3)
    p_run.add_argument(
        "--workers", type=int, default=4, help="Concurrent calls per probe (default 4)"
    )

    sub.add_parser("report", help="Aggregate runs into data/latest.json")
    sub.add_parser("site", help="Render docs/ from data/latest.json")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        if args.judges:
            specs = [runner.parse_judge_arg(a) for a in args.judges.split(",") if a.strip()]
        else:
            specs = runner.load_enabled_judges(args.judges_file)
        if not specs:
            parser.exit(
                1,
                "No judges enabled. Pass --judges provider:model or set "
                "enabled: true in judges.yaml.\n",
            )
        out = args.out or str(Path("data/runs") / args.month)
        runner.run(
            args.month,
            out,
            specs,
            probeset_path=args.probeset,
            reps=args.reps,
            workers=args.workers,
        )
    elif args.cmd == "report":
        report.build_latest("data/runs", "data/latest.json")
    elif args.cmd == "site":
        sitegen.build_site("data/latest.json", "docs")


if __name__ == "__main__":
    main()
