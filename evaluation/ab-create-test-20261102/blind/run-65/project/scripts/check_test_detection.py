#!/usr/bin/env python3
"""Prove behavioral tests reject isolated defects without editing the product."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('reuse_voided_id', "max((item['id'] for item in entries), default=0)",
     "max((item['id'] for item in entries if not item['voided']), default=0)", 'C03'),
    ('count_voided_in_summary', "active = [item for item in entries if not item['voided']]",
     'active = entries', 'C04'),
    ('strip_title', "'title': args.title,", "'title': args.title.strip(),", 'C02'),
    ('accept_zero', 'args.cents <= 0', 'args.cents < 0', 'C06'),
    ('reverse_list', 'result = entries', 'result = list(reversed(entries))', 'C02'),
    ('overwrite_category_sum', "by_category.get(item['category'], 0) + item['cents']",
     "item['cents']", 'C05'),
]


def main():
    source = (ROOT / 'expense_cli.py').read_text()
    failed = False
    with tempfile.TemporaryDirectory(prefix='ledger-mutations-') as directory:
        temporary_root = Path(directory)
        for name, old, new, case in MUTATIONS:
            if source.count(old) != 1:
                raise RuntimeError('Mutation anchor changed: ' + name)
            candidate = temporary_root / (name + '.py')
            candidate.write_text(source.replace(old, new))
            env = dict(os.environ, LEDGER_TEST_CLI=str(candidate))
            result = subprocess.run(
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                 '-p', 'test_behavior.py', '-k', case, '-v'], cwd=ROOT,
                env=env, capture_output=True, text=True, timeout=30)
            # Require a real assertion failure, not import errors or a broken launch.
            detected = result.returncode != 0 and 'FAIL:' in result.stderr and 'AssertionError' in result.stderr
            print('{}: {} (case {}, exit {})'.format(name, 'DETECTED' if detected else 'MISSED', case, result.returncode))
            print(result.stdout + result.stderr)
            failed |= not detected
    cleaned = not temporary_root.exists()
    print('Temporary mutation directory removed:', cleaned)
    return int(failed or not cleaned)


if __name__ == '__main__':
    sys.exit(main())
