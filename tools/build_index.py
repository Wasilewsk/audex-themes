#!/usr/bin/env python3
"""Validate every theme package and (re)build index.json.

Run from the store root:

    python3 tools/build_index.py          # rewrite index.json
    python3 tools/build_index.py --check  # fail if index.json is stale

CI runs the --check form so a pull request cannot add a package without an
updated index.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from theme_store import (  # noqa: E402
    INDEX_NAME,
    ThemeError,
    collect_packages,
    render_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that index.json matches the packages instead of writing it",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="store root (defaults to the repository root)",
    )
    args = parser.parse_args()

    try:
        entries = collect_packages(args.root)
    except ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    rendered = render_index(entries)
    index_path = args.root / INDEX_NAME

    if args.check:
        try:
            current = index_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"error: {INDEX_NAME} is missing; run tools/build_index.py", file=sys.stderr)
            return 1
        if current != rendered:
            print(
                f"error: {INDEX_NAME} is out of date; run tools/build_index.py and commit it",
                file=sys.stderr,
            )
            return 1
        print(f"index is valid: {len(entries)} theme(s)")
        return 0

    index_path.write_text(rendered, encoding="utf-8")
    print(f"wrote {INDEX_NAME}: {len(entries)} theme(s)")
    for entry in entries:
        print(f"  {entry['name']} ({entry['id']}) {entry['version']} - {entry['size']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
