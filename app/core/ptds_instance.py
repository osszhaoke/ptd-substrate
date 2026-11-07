"""Creates an instance directory (the only writer of instance.json). Run once per instance.

    python3 ptds_instance.py --root ~/PTDS-instances --id synthetic-example --kind DEMO \
        --tz Asia/Shanghai --name "演示实例 · 合成病例 C2"

There is no default time zone and no default kind: both must be given explicitly.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from h1_common import init_instance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--kind", required=True, choices=["DEMO", "REAL"])
    parser.add_argument("--tz", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--accept", choices=["SYNTHETIC","REAL"], nargs="+",
                        help="Data types accepted by this space, independent of its kind")
    args = parser.parse_args()
    if args.accept and len(set(args.accept)) != len(args.accept):
        parser.error("Each accepted data type may appear only once")
    created_at = datetime.now(ZoneInfo(args.tz)).isoformat(timespec="seconds")
    ctx = init_instance(args.root.expanduser(), args.id, args.kind, args.tz, args.name, created_at,
                        {"accept": args.accept} if args.accept else None)
    print(f"created {ctx.root} ({ctx.kind}, {ctx.tz})")


if __name__ == "__main__":
    main()
