"""CLI entry point: ``or2s``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from or2s_capture.rosbag import import_rosbag2
from or2s_capture.validate import validate
from or2s_capture.write import write_synthetic_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="or2s",
        description="Open Real2Sim capture bag tools",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_write = sub.add_parser(
        "write-synthetic",
        help="Write a synthetic RGB+pose capture session",
    )
    p_write.add_argument("out_dir", type=Path, help="Output session directory")
    p_write.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Capture duration in seconds (default: 30)",
    )
    p_write.add_argument(
        "--fps",
        type=float,
        default=20.0,
        help="Capture rate in frames per second (default: 20)",
    )

    p_val = sub.add_parser("validate", help="Validate a capture session")
    p_val.add_argument("session_dir", type=Path, help="Session directory")
    p_val.add_argument(
        "--json",
        action="store_true",
        help="Print report as JSON",
    )

    p_imp = sub.add_parser(
        "import-rosbag",
        help="Import rosbag2 into a capture session (stub)",
    )
    p_imp.add_argument("bag", type=Path, help="rosbag2 path")
    p_imp.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        required=True,
        help="Output session directory",
    )

    args = parser.parse_args(argv)

    if args.command == "write-synthetic":
        try:
            out = write_synthetic_session(
                args.out_dir,
                duration_s=args.duration,
                fps=args.fps,
            )
        except ValueError as e:
            parser.error(str(e))
        print(f"Wrote synthetic session: {out}")
        return 0

    if args.command == "validate":
        report = validate(args.session_dir)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            status = "OK" if report.ok else "FAIL"
            print(f"{status}  {report.path}")
            for e in report.errors:
                print(f"  error: {e}")
            for w in report.warnings:
                print(f"  warning: {w}")
        return 0 if report.ok else 1

    if args.command == "import-rosbag":
        try:
            import_rosbag2(args.bag, args.out_dir)
        except NotImplementedError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
