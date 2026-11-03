#!/usr/bin/env python3
"""Build the v0.5 blind review page from Sol's first run of each frozen prompt.

The page reuses the v0.4 layout and interaction. A and B are assigned with a
fixed seed, so regenerating gives the same pairs. Only key.json reveals versions.
"""
import json, random, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
V04 = HERE.parents[1] / 'v04/human-review/blind-review.html'
RESULTS = HERE.parent / 'results'
PROMPTS = json.loads((HERE.parent / 'prompts.json').read_text())
SEED = 20261103

order = [('S5', 'speech'), ('S6', 'speech'), ('S7', 'speech'), ('S8', 'speech'),
         ('AC10', 'acceptance'), ('AC11', 'acceptance')]
rng = random.Random(SEED)
qs, key = [], []
for n, (source, kind) in enumerate(order, 1):
    prompt = PROMPTS[kind][source] if kind == 'speech' else PROMPTS[kind][source]['prompt']
    answer = {}
    for arm in ['v04', 'v05']:
        record = json.loads((RESULTS / f'{source}-sol-{arm}-r1.json').read_text())
        answer[arm] = record['final']
    if rng.random() < 0.5:
        alias = {'A': 'v05', 'B': 'v04'}
    else:
        alias = {'A': 'v04', 'B': 'v05'}
    qs.append({'n': n, 'kind': kind, 'q': prompt, 'A': answer[alias['A']], 'B': answer[alias['B']]})
    key.append({'question': n, 'source': source, 'A': alias['A'], 'B': alias['B']})

qs_js = json.dumps(qs, ensure_ascii=False).replace('</', '<\\/')
html = V04.read_text(encoding='utf-8')
html = html.replace('<title>说人话盲看 第三轮</title>', '<title>说人话与验收标准盲看 · 第四轮</title>')
html = html.replace('<h1>说人话盲看 · 第三轮</h1>', '<h1>说人话与验收标准盲看 · 第四轮</h1>')
html = re.sub(r'(?m)^const QS=.*$', lambda _: f'const QS={qs_js};', html)
html = html.replace("const KEY='ytstack-blind-v04';", "const KEY='ytstack-blind-review-r4';")
html = html.replace(":'6 题都选完了，复制后贴回对话就行。'",
                    ":`${QS.length} 题都选完了，复制后贴回对话就行。`")
(HERE / 'blind-review.html').write_text(html, encoding='utf-8')
(HERE / 'key.json').write_text(json.dumps(key, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'built {len(qs)} questions, seed {SEED}')
