#!/usr/bin/env python3
"""Run the suite and prove selected regressions are detected in temporary copies."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'test-results'
COMMAND = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
MUTATIONS = [
    ('M01_void_included', "active = [item for item in entries if not item['voided']]",
     'active = entries', 'LL04'),
    ('M02_trim_title', "'title': args.title,", "'title': args.title.strip(),", 'LL02'),
    ('M03_reuse_void_id', "max((item['id'] for item in entries), default=0)",
     "max((item['id'] for item in entries if not item['voided']), default=0)", 'LL03'),
    ('M04_accept_zero', 'args.cents <= 0', 'args.cents < 0', 'LL05'),
    ('M05_remove_void_record', "entry['voided'] = True",
     "entry['voided'] = True\n        entries.remove(entry)", 'LL03'),
    ('M06_overwrite_category_total', "by_category.get(item['category'], 0) + item['cents']",
     "item['cents']", 'LL04'),
]


def run(directory):
    return subprocess.run(COMMAND, cwd=directory, capture_output=True, text=True,
                          encoding='utf-8', timeout=120)


def main():
    RESULTS.mkdir(exist_ok=True)
    files = [ROOT / 'README.md', ROOT / 'expense_cli.py', *sorted((ROOT / 'tests').glob('test_*.py')),
             Path(__file__).resolve(), ROOT / '.agents/skills/test-ledger-lite/SKILL.md']
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'command': COMMAND,
              'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in files}, 'mutations': []}
    baseline = run(ROOT)
    (RESULTS / 'baseline.log').write_text(baseline.stdout + baseline.stderr)
    report['baseline_returncode'] = baseline.returncode
    source = (ROOT / 'expense_cli.py').read_text()
    all_detected = baseline.returncode == 0
    if all_detected:
        for name, old, new, expected_case in MUTATIONS:
            if source.count(old) != 1:
                raise RuntimeError('Mutation anchor must occur exactly once: ' + name)
            with tempfile.TemporaryDirectory(prefix='ledger-mutation-') as directory:
                temporary = Path(directory)
                shutil.copytree(ROOT / 'tests', temporary / 'tests',
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                (temporary / 'expense_cli.py').write_text(source.replace(old, new), encoding='utf-8')
                result = run(temporary)
                output = result.stdout + result.stderr
                # A nonzero exit alone could be a broken harness. Require an assertion
                # failure from the intended behavioral case, with no test errors.
                detected = (result.returncode != 0 and 'FAIL: test_' + expected_case in output
                            and 'ERROR:' not in output)
                (RESULTS / (name + '.log')).write_text(output)
                report['mutations'].append({'name': name, 'expected_case': expected_case,
                                            'returncode': result.returncode,
                                            'detected': detected})
                all_detected = all_detected and detected
    report['passed'] = all_detected
    (RESULTS / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'baseline_returncode': baseline.returncode,
                      'mutations_detected': sum(m['detected'] for m in report['mutations']),
                      'mutations_total': len(MUTATIONS), 'passed': all_detected}))
    return 0 if all_detected else 1


if __name__ == '__main__':
    sys.exit(main())
