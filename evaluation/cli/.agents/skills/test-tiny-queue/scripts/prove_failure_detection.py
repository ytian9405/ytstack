#!/usr/bin/env python3
"""Run the unchanged TQ02 command against a disposable broken and restored CLI."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True,
                        help='New persistent evidence directory; must not exist')
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    live = ROOT / 'queue_cli.py'
    original = live.read_bytes()
    source = original.decode()
    write = "    args.state.write_text(json.dumps(rows, ensure_ascii=False) + '\\n')"
    report = {'status': 'BLOCKED', 'live_target_sha256_before': hashlib.sha256(original).hexdigest(),
              'case': 'TQ02', 'runs': []}
    scratch_path = None
    try:
        if source.count(write) != 1:
            raise RuntimeError('Write boundary changed; update isolated variant without weakening TQ02')
        variant = source.replace(write, '    pass  # Negative control: acknowledge mutation but omit persistence')
        (evidence / 'broken-queue_cli.py').write_text(variant)
        (evidence / 'mutation.patch').write_text(''.join(difflib.unified_diff(
            source.splitlines(True), variant.splitlines(True),
            fromfile='original/queue_cli.py', tofile='broken/queue_cli.py')))
        with tempfile.TemporaryDirectory(prefix='tiny-queue-negative-') as scratch:
            scratch_path = Path(scratch)
            target = scratch_path / 'queue_cli.py'
            shutil.copy2(live, target)
            target.write_text(variant)
            active = evidence / 'active.json'
            command = [sys.executable, str(ROOT / 'tests/test_queue_cli.py'), '--case', 'TQ02',
                       '--target', str(target), '--evidence', str(active)]
            report['exact_unchanged_test_command'] = shlex.join(command)
            for phase in ('broken', 'restored'):
                if phase == 'restored':
                    target.write_bytes(original)
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
                (evidence / (phase + '.log')).write_text(result.stdout + result.stderr)
                receipt = json.loads(active.read_text())
                active.rename(evidence / (phase + '.json'))
                report['runs'].append({'phase': phase, 'command': shlex.join(command),
                                       'exit_status': result.returncode,
                                       'receipt': phase + '.json', 'output': phase + '.log'})
                if phase == 'broken':
                    failing = [a for c in receipt['cases'] for a in c['assertions'] if a['status'] == 'FAIL']
                    if result.returncode != 1 or not any(
                            a['label'] == 'fresh process sees first persisted task'
                            and a['actual'] == []
                            and a['expected'] == [{'id': 1, 'title': '  Prepare slides 雪  ', 'done': False}]
                            for a in failing):
                        raise RuntimeError('Negative control did not fail at the intended persistence assertion')
                    report['detected_assertion'] = failing
                elif result.returncode != 0 or receipt['status'] != 'PASS':
                    raise RuntimeError('Restored isolated target did not pass TQ02')
            report['status'] = 'PASS'
    except Exception as exc:
        report['reason'] = str(exc)
    finally:
        report['cleanup'] = {'scratch_removed': scratch_path is None or not scratch_path.exists(),
                             'background_processes_started': [],
                             'live_target_sha256_after': hashlib.sha256(live.read_bytes()).hexdigest()}
        report['live_target_unchanged'] = live.read_bytes() == original
        report['evidence_files_after_cleanup'] = sorted(p.name for p in evidence.iterdir())
        (evidence / 'proof.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' and report['live_target_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
