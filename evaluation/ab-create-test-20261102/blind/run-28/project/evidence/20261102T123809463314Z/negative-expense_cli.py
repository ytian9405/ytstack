#!/usr/bin/env python3
"""A small persistent expense ledger with a public JSON CLI."""
import argparse
import json
from pathlib import Path
import sys


def load(state):
    return json.loads(state.read_text()) if state.exists() else []


def save(state, entries):
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text('[]\n')  # negative control: lose persisted entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('title')
    add.add_argument('--cents', type=int, required=True)
    add.add_argument('--category', required=True)
    commands.add_parser('list')
    void = commands.add_parser('void')
    void.add_argument('id', type=int)
    commands.add_parser('summary')
    args = parser.parse_args()
    entries = load(args.state)
    if args.command == 'add':
        if not args.title.strip() or not args.category.strip() or args.cents <= 0:
            print('title and category must be nonblank; cents must be positive', file=sys.stderr)
            return 1
        entry = {'id': max((item['id'] for item in entries), default=0) + 1,
                 'title': args.title, 'cents': args.cents,
                 'category': args.category, 'voided': False}
        entries.append(entry)
        save(args.state, entries)
        result = entry
    elif args.command == 'list':
        result = entries
    elif args.command == 'void':
        entry = next((item for item in entries if item['id'] == args.id), None)
        if entry is None:
            print('unknown expense id', file=sys.stderr)
            return 1
        entry['voided'] = True
        save(args.state, entries)
        result = entry
    else:
        active = [item for item in entries if not item['voided']]
        by_category = {}
        for item in active:
            by_category[item['category']] = by_category.get(item['category'], 0) + item['cents']
        result = {'count': len(active), 'total_cents': sum(item['cents'] for item in active),
                  'by_category': by_category}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
