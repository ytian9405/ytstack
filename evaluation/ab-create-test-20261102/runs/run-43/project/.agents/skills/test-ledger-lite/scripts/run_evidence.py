#!/usr/bin/env python3
"""Run the suite, prove assertion sensitivity in a disposable copy, rerun live suite."""
import datetime
import difflib
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'evidence' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT.mkdir(parents=True)
SUITE = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
CASE = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_behaviors.py', '-k', 'LL02', '-v']


def run(label, command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=120)
    (OUT / (label + '.log')).write_text(
        f'cwd: {cwd}\ncommand: {command!r}\nexit: {result.returncode}\n'
        + result.stdout + result.stderr)
    return result


def main():
    original = (ROOT / 'expense_cli.py').read_bytes()
    baseline = run('baseline', SUITE, ROOT)
    with tempfile.TemporaryDirectory(prefix='ledger-negative-') as scratch:
        variant = Path(scratch)
        shutil.copytree(ROOT / 'tests', variant / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
        source = original.decode()
        old = '    state.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + \'\\n\')'
        assert source.count(old) == 1
        broken = source.replace(old, '    pass  # negative control: discard writes')
        (variant / 'expense_cli.py').write_text(broken)
        (OUT / 'negative-control.patch').write_text(''.join(difflib.unified_diff(
            source.splitlines(True), broken.splitlines(True), fromfile='expense_cli.py', tofile='variant/expense_cli.py')))
        failure = run('negative-control', CASE, variant)
    restored = run('restored', SUITE, ROOT)
    sensitive = failure.returncode != 0 and 'AssertionError: Lists differ: [] !=' in failure.stderr
    unchanged = (ROOT / 'expense_cli.py').read_bytes() == original
    clean = not variant.exists()
    ok = baseline.returncode == 0 and restored.returncode == 0 and sensitive and unchanged and clean
    (OUT / 'receipt.txt').write_text(
        f'target: {ROOT / "expense_cli.py"}\nsha256: {hashlib.sha256(original).hexdigest()}\n'
        f'LL01–LL05 and original smoke: {"PASS" if baseline.returncode == 0 else "FAIL"}\n'
        f'negative control assertion detected: {sensitive}\n'
        f'follow-up suite exit: {restored.returncode}\nlive target unchanged: {unchanged}\n'
        f'negative-control scratch removed: {clean}\n'
        'Test TemporaryDirectory state removed by unittest addCleanup on success and failure.\n'
        'No server, port, credentials, or background process required.\n')
    print(OUT.relative_to(ROOT))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
