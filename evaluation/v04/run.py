#!/usr/bin/env python3
"""Run the frozen v0.4 prompts: speech v0.2 vs v0.4, acceptance v0.1 vs v0.4."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v02'))
import harness
REPO = Path(__file__).resolve().parents[2]
harness.PACKAGES['v04'] = REPO
VOICE = {'v02': str(REPO / 'evaluation/snapshots/v02/voice/plain-talk.md'), 'v04': str(REPO / 'voice/plain-talk.md')}
P = json.loads((Path(__file__).parent / 'prompts.json').read_text())
jobs = []
for kind, arms in [('speech', ['v02', 'v04']), ('acceptance', ['v01', 'v04'])]:
    for k, v in P[kind].items():
        prompt = v if kind == 'speech' else v['prompt']
        for m, reps in [('gpt-6.1-sol', 2), ('gpt-6-astra', 1)]:
            for r in range(1, reps + 1):
                for arm in arms:
                    j = {'id': f'{k}-{m.split("-")[-1]}-{arm}-r{r}', 'prompt': prompt, 'model': m, 'package': arm}
                    if arm in VOICE:
                        j['agents_md'] = VOICE[arm]
                    jobs.append(j)
out = Path(__file__).parent / 'results'
Path('/tmp/ytev/jobs-v04.json').write_text(json.dumps(jobs, ensure_ascii=False))
sys.argv = ['harness', '/tmp/ytev/jobs-v04.json', '--out', str(out), '--workers', '16']
harness.main()
