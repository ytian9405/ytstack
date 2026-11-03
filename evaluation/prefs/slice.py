#!/usr/bin/env python3
"""Merge Codex slices with rows mined from other tools, cut month slices.

Input is the slice1.md that mine.py --slices 1 wrote (blocks headed
`### 第1段-n | 日期 | 项目 xxx`, split on '\n### ') plus the rows.jsonl from
mine_other.py. Entries are merged, sorted by date, grouped by month: months
under 30k chars merge with a neighbour, months over 150k chars split in two or
more chronological parts. Output keeps the mine.py block format with a source
column added, and a copy of prompt.md lands next to the slices.

    python3 evaluation/prefs/slice.py --codex ~/.ytstack-prefs/codex/slice1.md \
        --rows ~/.ytstack-prefs/other/rows.jsonl --out ~/.ytstack-prefs/slices
"""
import argparse
import json
import math
import re
import shutil
from pathlib import Path

MONTH_MAX = 150_000   # a month above this many chars is split further
MONTH_MERGE = 30_000  # a month below this can merge with its neighbour
HEADER = re.compile(r'### 第\d+段-\d+ \| (\d{4}-\d{2}-\d{2}) \| 项目 (.*)')


def parse_codex(path):
    text = path.read_text()
    entries = []
    for block in text.split('\n### '):
        block = block.strip('\n')
        if not block:
            continue
        if not block.startswith('### '):
            block = '### ' + block
        head, _, body = block.partition('\n')
        match = HEADER.match(head)
        if not match:
            continue
        body = body[len('[AI 上一条回复]'):].lstrip('\n')
        before, sep, user = body.partition('\n[用户]\n')
        entries.append({'date': match.group(1), 'source': 'codex',
                        'project': match.group(2).strip(),
                        'before': before.strip(), 'user': user.strip()})
    return entries


def load_rows(path):
    entries = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            entries.append({'date': row['date'], 'source': row['source'],
                            'project': row.get('project', '?'),
                            'before': row.get('before', ''), 'user': row.get('user', '')})
    return entries


def group_months(entries):
    groups = []
    for entry in sorted(entries, key=lambda e: e['date']):  # stable: keeps input order per date
        month = entry['date'][:7]
        if groups and groups[-1][0][-1] == month:
            groups[-1][1].append(entry)
        else:
            groups.append(([month], [entry]))
    return groups


def size_of(items):
    return sum(len(e['before']) + len(e['user']) for e in items)


def plan_slices(groups):
    """Merge small months with the previous one, then split oversized groups."""
    merged = []
    for months, items in groups:
        if merged and size_of(items) < MONTH_MERGE:
            merged[-1][0].extend(months)
            merged[-1][1].extend(items)
        else:
            merged.append((months, items))
    planned = []
    for months, items in merged:
        total = size_of(items)
        parts = max(1, math.ceil(total / MONTH_MAX))
        if parts == 1:
            planned.append((months, items))
            continue
        target = total / parts
        chunks, current, current_size = [], [], 0
        for entry in items:
            current.append(entry)
            current_size += len(entry['before']) + len(entry['user'])
            if current_size >= target and len(chunks) < parts - 1:
                chunks.append(current)
                current, current_size = [], 0
        if current:
            chunks.append(current)
        for chunk in chunks:
            planned.append((months, chunk))
    return planned


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--codex', type=Path, required=True,
                        help='slice1.md written by mine.py --slices 1.')
    parser.add_argument('--rows', type=Path, default=Path.home() / '.ytstack-prefs' / 'other' / 'rows.jsonl',
                        help='rows.jsonl written by mine_other.py.')
    parser.add_argument('--out', type=Path, default=Path.home() / '.ytstack-prefs' / 'slices')
    args = parser.parse_args()
    entries = parse_codex(args.codex)
    if args.rows.exists():
        entries += load_rows(args.rows)
    else:
        print(json.dumps({'warning': f'rows file not found: {args.rows}'}, ensure_ascii=False))
    planned = plan_slices(group_months(entries))
    args.out.mkdir(parents=True, exist_ok=True)
    report = []
    for number, (months, items) in enumerate(planned, 1):
        blocks = []
        for n, entry in enumerate(items, 1):
            before = entry['before']
            if len(before) > 1200:
                before = before[:700] + ' …… ' + before[-500:]
            head = (f"### 第{number}段-{n} | {entry['date']} | {entry['source']} "
                    f"| 项目 {entry['project']}")
            blocks.append(f"{head}\n[AI 上一条回复]\n{before or '（会话开头）'}\n[用户]\n{entry['user']}\n")
        path = args.out / f'slice{number}.md'
        path.write_text('\n'.join(blocks))
        report.append({'file': path.name, 'months': '-'.join((months[0], months[-1])) if len(months) > 1 else months[0],
                       'from': items[0]['date'], 'to': items[-1]['date'],
                       'entries': len(items), 'chars': size_of(items)})
    shutil.copy2(Path(__file__).with_name('prompt.md'), args.out / 'prompt.md')
    print(json.dumps({'out': str(args.out), 'total_entries': len(entries), 'slices': report},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
