#!/usr/bin/env python3
"""Print a ledger summary plus a yuan display."""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: yuan_view.py LEDGER.json', file=sys.stderr)
        return 2
    entries = json.loads(Path(sys.argv[1]).read_text())
    active = [item for item in entries if not item['voided']]
    by_category = {}
    for item in active:
        by_category[item['category']] = by_category.get(item['category'], 0) + item['cents']
    total = sum(item['cents'] for item in active)
    result = {
        'count': len(active),
        'total_cents': total,
        'display_yuan': total // 100,
        'by_category': by_category,
        'by_category_yuan': {key: value // 100 for key, value in by_category.items()},
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
