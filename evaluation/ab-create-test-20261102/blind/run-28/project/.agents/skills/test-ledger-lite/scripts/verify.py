#!/usr/bin/env python3
"""Retain native test output and prove failure detection without editing live code."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / 'evidence' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
EVIDENCE.mkdir(parents=True)
ENV = dict(os.environ, LEDGER_TRACE='1', PYTHONDONTWRITEBYTECODE='1')
SUITE = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
CASE = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
        '-p', 'test_behavior.py', '-k', 'LL02', '-v']
receipts = []


def run(label, cwd, command):
    result = subprocess.run(command, cwd=cwd, env=ENV, capture_output=True,
                            text=True, timeout=120)
    (EVIDENCE / (label + '.log')).write_text(result.stdout + result.stderr)
    receipts.append({'label': label, 'cwd': str(cwd), 'command': command,
                     'exit_code': result.returncode, 'log': label + '.log'})
    return result


def main():
    source = (ROOT / 'expense_cli.py').read_text()
    baseline = run('baseline', ROOT, SUITE)
    scratch = None
    try:
        with tempfile.TemporaryDirectory(prefix='negative-control-', dir=EVIDENCE) as directory:
            scratch = Path(directory)
            shutil.copytree(ROOT / 'tests', scratch / 'tests',
                            ignore=shutil.ignore_patterns('__pycache__'))
            needle = '    state.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + \'\\n\')'
            if source.count(needle) != 1:
                raise RuntimeError('Negative control write boundary changed; review variant')
            variant = source.replace(needle, "    state.write_text('[]\\n')  # negative control: lose persisted entries")
            (scratch / 'expense_cli.py').write_text(variant)
            (EVIDENCE / 'negative-expense_cli.py').write_text(variant)
            negative = run('negative-control', scratch, CASE)
        restored = run('restored', ROOT, SUITE)
        detected = (negative.returncode != 0 and 'FAIL: test_LL02_add_persistence' in negative.stderr
                    and 'Lists differ: [] !='  in negative.stderr)
        outcome = baseline.returncode == 0 and restored.returncode == 0 and detected
        receipt = {'python': platform.python_version(), 'target': str(ROOT / 'expense_cli.py'),
                   'target_sha256': hashlib.sha256(source.encode()).hexdigest(),
                   'runs': receipts, 'product_cases': {f'LL0{i}': 'PASS' if restored.returncode == 0 else 'FAIL'
                                                      for i in range(1, 6)},
                   'failure_detection': 'PASS' if detected else 'FAIL',
                   'scratch_removed': not scratch.exists(),
                   'live_target_unchanged': (ROOT / 'expense_cli.py').read_text() == source}
        (EVIDENCE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(str(EVIDENCE))
        return 0 if outcome else 1
    finally:
        (EVIDENCE / 'commands.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    sys.exit(main())
