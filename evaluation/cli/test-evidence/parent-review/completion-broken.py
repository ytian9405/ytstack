#!/usr/bin/env python3
"""A small persistent task queue, exposed through a JSON CLI."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True, type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('title')
    commands.add_parser('list')
    complete = commands.add_parser('complete')
    complete.add_argument('id', type=int)
    args = parser.parse_args()
    rows = json.loads(args.state.read_text()) if args.state.exists() else []
    if args.command == 'list':
        print(json.dumps(rows, ensure_ascii=False))
        return
    if args.command == 'add':
        if not args.title.strip():
            parser.error('title must contain text')
        row = {'id': max((r['id'] for r in rows), default=0) + 1,
               'title': args.title, 'done': False}
        rows.append(row)
    else:
        row = next((r for r in rows if r['id'] == args.id), None)
        if row is None:
            parser.error('task does not exist')
        row['done'] = False
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(rows, ensure_ascii=False) + '\n')
    print(json.dumps(row, ensure_ascii=False))


if __name__ == '__main__':
    main()
