"""Apply the preregistered common unittest and hidden mutation checks."""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from mutations import MUTATIONS, EQUIVALENT, apply

BASE = Path(__file__).resolve().parents[1]
FIXTURE = BASE / 'fixture'
COMMAND = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root):
    return {str(p.relative_to(root)): digest(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
            and '.agents/skills/create-test-skill/' not in str(p.relative_to(root))}


def copy_project(source, destination):
    def ignore(directory, names):
        result = {name for name in names if name in {'__pycache__', '.git'} or name.endswith('.pyc')}
        if Path(directory) == source / '.agents/skills':
            result.add('create-test-skill')
        return result
    shutil.copytree(source, destination, ignore=ignore, symlinks=True)


def run_case(source, output, name, variant=None, old_only=False):
    with tempfile.TemporaryDirectory(prefix='ledger-eval-') as scratch:
        target = Path(scratch) / 'project'
        copy_project(source, target)
        product = target / 'expense_cli.py'
        original = product.read_text()
        if variant is not None:
            product.write_text(apply(original, variant))
            (output / f'{name}.patch').write_text(''.join(difflib.unified_diff(
                original.splitlines(keepends=True), product.read_text().splitlines(keepends=True),
                fromfile='a/expense_cli.py', tofile='b/expense_cli.py')))
        # Attribute old coverage using the identical original smoke test alone.
        command = ([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_smoke.py', '-v']
                   if old_only else COMMAND)
        before = snapshot(target)
        started = time.monotonic()
        entry = {'command': command, 'cwd': str(target), 'target_sha256': digest(product),
                 'started_at': datetime.now(timezone.utc).isoformat()}
        try:
            result = subprocess.run(command, cwd=target, capture_output=True, text=True, timeout=60)
            entry.update(exit_status=result.returncode, stdout=result.stdout, stderr=result.stderr)
            matches = re.findall(r'Ran (\d+) tests?', result.stderr)
            entry['tests_run'] = int(matches[-1]) if matches else None
            entry['status'] = 'PASS' if result.returncode == 0 and entry['tests_run'] else 'FAIL'
        except subprocess.TimeoutExpired as error:
            entry.update(status='BLOCKED', exit_status=None,
                         stdout=(error.stdout or b'').decode() if isinstance(error.stdout, bytes) else error.stdout or '',
                         stderr=(error.stderr or b'').decode() if isinstance(error.stderr, bytes) else error.stderr or '',
                         reason='Common 60-second limit reached')
        entry['elapsed_seconds'] = round(time.monotonic() - started, 3)
        after = snapshot(target)
        entry['changed_paths'] = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
        (output / f'{name}.stdout.log').write_text(entry['stdout'])
        (output / f'{name}.stderr.log').write_text(entry['stderr'])
        # A nonzero exit is a candidate only. Astra must verify intended failure attribution.
        entry['candidate_kill'] = variant is not None and entry['exit_status'] not in (0, None)
        entry['scratch'] = scratch
    entry['scratch_removed'] = not Path(scratch).exists()
    (output / f'{name}.json').write_text(json.dumps(entry, ensure_ascii=False, indent=2) + '\n')
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label')
    parser.add_argument('--old-only', action='store_true')
    args = parser.parse_args()
    if args.old_only:
        source, label = FIXTURE, 'original-smoke'
    elif args.label and re.fullmatch(r'run-\d+', args.label):
        label = args.label
        source = BASE / 'runs' / label / 'project'
    else:
        parser.error('Use --old-only or --label run-NN')
    output = BASE / 'objective' / label
    output.mkdir(parents=True, exist_ok=False)
    original_inputs = {str(p.relative_to(FIXTURE)): digest(p) for p in FIXTURE.rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts}
    integrity = {name: (source / name).is_file() and digest(source / name) == value
                 for name, value in original_inputs.items()}
    report = {'label': label, 'source_inputs_preserved': integrity,
              'artifact_sha256': snapshot(source), 'results': {}, 'mutation_policy': 'candidate kills require intended-behavior review'}
    stages = [('clean-1', None), ('clean-2', None), *MUTATIONS.items(), ('equivalent', EQUIVALENT), ('restored', None)]
    for name, variant in stages:
        report['results'][name] = run_case(source, output, name, variant, old_only=args.old_only)
    report['clean_pass'] = all(report['results'][name]['status'] == 'PASS' for name in ['clean-1', 'clean-2', 'restored'])
    report['candidate_kills'] = [name for name in MUTATIONS if report['results'][name]['candidate_kill']] if report['clean_pass'] else []
    report['survived'] = [name for name in MUTATIONS if report['results'][name]['exit_status'] == 0]
    report['all_owned_scratch_removed'] = all(value['scratch_removed'] for value in report['results'].values())
    (output / 'objective.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'label': label, 'clean_pass': report['clean_pass'], 'candidate_kills': len(report['candidate_kills']), 'survived': report['survived'], 'equivalent': report['results']['equivalent']['status'], 'inputs_preserved': all(integrity.values())}))


if __name__ == '__main__':
    main()
