#!/usr/bin/env python3
"""A small temperature logger with a public JSON CLI."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def load(path):
    return json.loads(path.read_text()) if path.exists() else []


def save(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('logger.json'))
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('sensor')
    add.add_argument('temp', type=float)
    add.add_argument('--at', default=None)
    stats = commands.add_parser('stats')
    stats.add_argument('--sensor', required=True)
    commands.add_parser('list')
    args = parser.parse_args()
    rows = load(args.state)
    if args.command == 'list':
        result = rows
    elif args.command == 'add':
        try:
            config = json.loads(args.config.read_text())
        except (FileNotFoundError, ValueError):
            config = {}
        names = config.get('sensors', {})
        if args.sensor not in names:
            print('unknown sensor id', file=sys.stderr)
            return 1
        stamp = args.at or datetime.now().strftime('%Y-%m-%dT%H:%M')
        row = {'id': max((item['id'] for item in rows), default=0) + 1,
               'sensor': args.sensor, 'temp_c': args.temp, 'at': stamp}
        rows.append(row)
        save(args.state, rows)
        result = row
    else:
        picked = [item for item in rows if item['sensor'] == args.sensor]
        temps = [item['temp_c'] for item in picked]
        result = {'sensor': args.sensor, 'count': len(picked),
                  'min_c': min(temps) if temps else None,
                  'max_c': max(temps) if temps else None,
                  'avg_c': round(sum(temps) / len(temps), 1) if temps else None}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
