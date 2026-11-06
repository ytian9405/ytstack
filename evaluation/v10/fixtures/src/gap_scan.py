#!/usr/bin/env python3
"""Scan readings for hours that have no record; print sensor, date, missing hours."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.state.read_text())
    seen = set()
    for row in rows:
        seen.add((row['sensor'], row['at'][:13]))
    gaps = {}
    for sensor in sorted({row['sensor'] for row in rows}):
        for day in sorted({at[:10] for who, at in seen if who == sensor}):
            for hour in range(24):
                if (sensor, f'{day}T{hour:02d}') not in seen:
                    gaps.setdefault((sensor, day), []).append(str(hour))
    for (sensor, day), hours in sorted(gaps.items()):
        print(f'{sensor}\t{day}\t{",".join(hours)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
