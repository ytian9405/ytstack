#!/usr/bin/env python3
"""Compare v07 question text with the frozen questions in v02, v03, v04, and v05.

Prints the closest pairs. Exit 0. The question text is the prompt the model
sees, including both turns and the trigger sentences. Rubric fields are not
compared. Result logs are not compared; they repeat the same frozen prompts.
"""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NEW = REPO / 'evaluation/v07/prompts.json'
OLD_FILES = (
    REPO / 'evaluation/v02/speech-prompts.json',
    REPO / 'evaluation/v02/trigger-prompts.json',
    REPO / 'evaluation/v02/acceptance-tasks.json',
    REPO / 'evaluation/v03/prompts.json',
    REPO / 'evaluation/v04/prompts.json',
    REPO / 'evaluation/v05/prompts.json',
)
SKIP_KEYS = {'_note', '_runner'}
NEW_KEYS = ('prompt', 'followup', '第一轮', '第二轮')


def squeeze(text):
    return re.sub(r'\s+', '', text)


def walk(value, path, found):
    if isinstance(value, str):
        text = value.strip()
        if len(squeeze(text)) >= 8:
            found.append((path, text))
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in SKIP_KEYS:
                continue
            walk(item, f'{path}.{key}', found)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk(item, f'{path}[{index}]', found)


def new_strings(data):
    found = []
    for key, value in data.items():
        if key in SKIP_KEYS or key == 'triggers':
            continue
        if isinstance(value, dict):
            for field in NEW_KEYS:
                if field in value:
                    found.append((f'v07:{key}.{field}', value[field].strip()))
    triggers = data.get('triggers', {})
    for skill, groups in triggers.items():
        if skill.startswith('_') or not isinstance(groups, dict):
            continue
        for label, items in groups.items():
            if isinstance(items, list):
                for index, item in enumerate(items):
                    found.append((f'v07:triggers.{skill}.{label}[{index}]', item.strip()))
    return found


def old_strings():
    found = []
    seen = set()
    for path in OLD_FILES:
        data = json.loads(path.read_text())
        local = []
        walk(data, path.relative_to(REPO).as_posix(), local)
        for label, text in local:
            key = squeeze(text)
            if key in seen:
                continue
            seen.add(key)
            found.append((label, text))
    return found


def main():
    data = json.loads(NEW.read_text())
    for key in ('K1', 'K2', 'H1'):
        question = data[key]
        if question['prompt'] != question['第一轮'] or question['followup'] != question['第二轮']:
            raise SystemExit(f'{key} prompt/followup drifted from 第一轮/第二轮')
    fresh = new_strings(data)
    previous = old_strings()
    ranked = []
    for new_label, new_text in fresh:
        new_key = squeeze(new_text)
        for old_label, old_text in previous:
            old_key = squeeze(old_text)
            if new_key == old_key:
                score = 1.0
            else:
                score = SequenceMatcher(None, new_key, old_key).ratio()
            ranked.append((score, new_label, new_text, old_label, old_text))
    ranked.sort(key=lambda item: item[0], reverse=True)
    print(f'compared {len(fresh)} new strings with {len(previous)} unique old strings')
    print('top 3 by SequenceMatcher on whitespace-stripped text:')
    for index, (score, new_label, new_text, old_label, old_text) in enumerate(ranked[:3], 1):
        print(f'{index}. {score:.3f}')
        print(f'   new: {new_label}')
        print(f'        {new_text[:180]}')
        print(f'   old: {old_label}')
        print(f'        {old_text[:180]}')
    close = [item for item in ranked if item[0] >= 0.45]
    print(f'pairs at or above 0.45: {len(close)}')
    for score, new_label, new_text, old_label, old_text in close[:12]:
        print(f'- {score:.3f} {new_label} <> {old_label}')
    blind = [item for item in ranked if item[1].startswith('v07:K') or item[1].startswith('v07:H')
             or item[1].startswith('v07:T') or item[1].startswith('v07:I') or item[1].startswith('v07:J')]
    print('top 3 among the seven blind prompts:')
    seen = set()
    shown = 0
    for score, new_label, new_text, old_label, old_text in blind:
        identity = (new_label.split('.')[0], old_label, score)
        if identity in seen:
            continue
        seen.add(identity)
        shown += 1
        print(f'{shown}. {score:.3f} {new_label} <> {old_label}')
        print(f'   new: {new_text[:120]}')
        print(f'   old: {old_text[:120]}')
        if shown == 3:
            break


if __name__ == '__main__':
    main()
