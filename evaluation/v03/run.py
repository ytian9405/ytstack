#!/usr/bin/env python3
"""Run the frozen v0.3 prompts with the v0.2 harness, comparing package snapshots."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v02'))
import harness
REPO = Path(__file__).resolve().parents[2]
harness.PACKAGES.update({'v03': REPO})
VOICE = {'v02': str(REPO / 'evaluation/snapshots/v02/voice/plain-talk.md'), 'v03': str(REPO / 'voice/plain-talk.md')}
P = json.loads((Path(__file__).parent / 'prompts.json').read_text())
jobs = []
for k, q in P['speech'].items():
    for m, reps in [('gpt-6.1-sol', 2), ('gpt-6-astra', 1)]:
        for r in range(1, reps + 1):
            for arm in ['v02', 'v03']:
                jobs.append({'id': f'{k}-{m.split("-")[-1]}-{arm}-r{r}', 'prompt': q, 'model': m, 'package': arm, 'agents_md': VOICE[arm]})
for k, t in P['acceptance'].items():
    for m, reps in [('gpt-6.1-sol', 2), ('gpt-6-astra', 1)]:
        for r in range(1, reps + 1):
            for arm in ['v01', 'v02', 'v03']:
                j = {'id': f'{k}-{m.split("-")[-1]}-{arm}-r{r}', 'prompt': t['prompt'], 'model': m, 'package': arm}
                if arm != 'v01':
                    j['agents_md'] = VOICE[arm]
                jobs.append(j)
Path('/tmp/ytev/jobs-v03.json').write_text(json.dumps(jobs, ensure_ascii=False))
sys.argv = ['harness', '/tmp/ytev/jobs-v03.json', '--out', '/tmp/ytev/v03', '--workers', '16']
harness.main()
