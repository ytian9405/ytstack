#!/usr/bin/env python3
"""Scan a ledger for entries sharing title and cents; print the id groups."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.state.read_text())
    groups = {}
    for row in rows:
        if row.get('voided'):
            continue
        groups.setdefault((row['title'], row['cents']), []).append(row['id'])
    for (title, cents), ids in sorted(groups.items()):
        if len(ids) > 1:
            print(f'{title}\t{cents}\t{",".join(str(item) for item in ids)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
