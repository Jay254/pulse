"""Command line entry point: `pulse digest`."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from pulse.digest import DEFAULT_LIMIT, default_collectors, run_digest
from pulse.store import Store


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulse")
    sub = parser.add_subparsers(dest="command", required=True)
    digest = sub.add_parser("digest", help="collect items and write today's digest")
    digest.add_argument("--db", default="data/pulse.db", help="SQLite database path")
    digest.add_argument("--out", default="digests", help="directory for digest files")
    digest.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="items per digest")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with Store(args.db) as store:
        path = run_digest(store, default_collectors(), args.out, limit=args.limit)
    print(path)
    return 0
