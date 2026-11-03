#!/usr/bin/env python3
"""Run the frozen v0.5 prompts: speech v0.4 vs v0.5, acceptance v0.4 vs v0.5."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v02'))
import harness
REPO = Path(__file__).resolve().parents[2]
harness.PACKAGES['v04'] = REPO / 'evaluation/snapshots/v04'
harness.PACKAGES['v05'] = REPO
VOICE = {'v04': str(REPO / 'evaluation/snapshots/v04/voice/plain-talk.md'), 'v05': str(REPO / 'voice/plain-talk.md')}
P = json.loads((Path(__file__).parent / 'prompts.json').read_text())
jobs = []
for kind, arms in [('speech', ['v04', 'v05']), ('acceptance', ['v04', 'v05'])]:
    for k, v in P[kind].items():
        prompt = v if kind == 'speech' else v['prompt']
        for m, reps in [('gpt-6.1-sol', 2), ('gpt-6-astra', 1)]:
            for r in range(1, reps + 1):
                for arm in arms:
                    j = {'id': f'{k}-{m.split("-")[-1]}-{arm}-r{r}', 'prompt': prompt, 'model': m, 'package': arm}
                    # Only the speech arm swaps the standing voice rules; the acceptance arm differs by package only.
                    if kind == 'speech' and arm in VOICE:
                        j['agents_md'] = VOICE[arm]
                    jobs.append(j)
out = Path(__file__).parent / 'results'
Path('/tmp/ytev/jobs-v05.json').write_text(json.dumps(jobs, ensure_ascii=False))
sys.argv = ['harness', '/tmp/ytev/jobs-v05.json', '--out', str(out), '--workers', '16']
harness.main()
