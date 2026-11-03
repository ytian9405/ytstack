#!/usr/bin/env python3
"""Run native unittest cases with public CLI transcripts and durable receipts."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    'YT01': 'test_package_integrity',
    'YT02': 'test_dependency_is_installed_and_repeat_is_harmless',
    'YT03': 'test_conflict_is_preserved_without_partial_installation',
    'YT04': 'test_dry_run_changes_nothing',
    'YT05': 'test_copied_claude_skills_are_standalone',
    'YT06': 'test_copy_does_not_claim_a_link_is_standalone',
    'YT07': 'test_project_install_does_not_follow_discovery_outside_project',
    'YT08': 'test_default_links_survive_bundle_move_for_both_hosts',
    'YT09': 'test_voice_block_keeps_user_content_and_repeat_is_harmless',
    'YT10': 'test_voice_dry_run_and_stale_block_update',
}


def identity(root):
    files = [root / name for name in ['ytstack.json', 'provenance.json', 'LICENSE']]
    for name in ['tools', 'skills', 'voice', '.claude-plugin']:
        files.extend(p for p in (root / name).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files) if p.is_file()}


def save(path, receipt):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')


def doctor(root):
    required = ['tools/install.py', 'tools/validate.py', 'ytstack.json', 'provenance.json',
                'LICENSE', '.claude-plugin/plugin.json']
    required.extend(f'skills/{name}/SKILL.md' for name in
                    ['create-test-skill', 'bro', 'technical-bro', 'unslop'])
    missing = [name for name in required if not (root / name).is_file()]
    if sys.version_info < (3, 9):
        return {'status': 'BLOCKED', 'reason': 'Python 3.9+ is required'}
    if missing:
        return {'status': 'BLOCKED', 'reason': 'Missing target inputs', 'missing': missing}
    command = [sys.executable, str(root / 'tools/install.py'), '--help']
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=15)
    manifest = json.loads((root / 'ytstack.json').read_text())
    return {'status': 'PASS' if result.returncode == 0 else 'BLOCKED',
            'name': manifest.get('name'), 'version': manifest.get('version'),
            'command': command, 'cwd': str(root), 'stdout': result.stdout,
            'stderr': result.stderr, 'exit_status': result.returncode}


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []

    def startTest(self, test):
        super().startTest(test)
        self.current = {'id': next(key for key, value in CASES.items()
                                   if value == test._testMethodName),
                        'test': test.id(), 'status': 'PASS', 'failures': []}
        self.started = time.monotonic()

    def failure(self, err, status):
        self.current['status'] = status
        self.current['failures'].append(''.join(traceback.format_exception(*err)))

    def addFailure(self, test, err):
        self.failure(err, 'FAIL')
        super().addFailure(test, err)

    def addError(self, test, err):
        self.failure(err, 'BLOCKED' if issubclass(err[0], (OSError, subprocess.TimeoutExpired)) else 'FAIL')
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.failure(err, 'FAIL')
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        self.current.update(status='SKIPPED', reason=reason)
        super().addSkip(test, reason)

    def stopTest(self, test):
        self.current.update(actions=getattr(test, 'actions', []),
                            elapsed_seconds=round(time.monotonic() - self.started, 3),
                            scratch=[{'path': path, 'removed': not Path(path).exists()}
                                     for path in getattr(test, 'scratch_paths', [])])
        self.cases.append(self.current)
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=ROOT,
                        help='Package root; tests remain those bundled with this project')
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--doctor', action='store_true')
    parser.add_argument('--evidence', type=Path, required=True,
                        help='Use a new JSON path to preserve earlier runs')
    args = parser.parse_args()
    if args.doctor and args.case:
        parser.error('--doctor and --case cannot be combined')
    if args.evidence.exists():
        parser.error('Evidence already exists; choose a new path')
    root = args.target.resolve()
    receipt = {'command': [sys.executable, *sys.argv], 'cwd': str(Path.cwd()),
               'target': str(root), 'python': sys.version,
               'started_at': datetime.now(timezone.utc).isoformat(), 'cases': []}
    try:
        receipt['doctor'] = doctor(root)
        if receipt['doctor']['status'] != 'PASS':
            receipt['status'] = 'BLOCKED'
            save(args.evidence, receipt)
            print(f'BLOCKED: {args.evidence}')
            return 2
        receipt['target_before'] = identity(root)
        if args.doctor:
            receipt['status'] = 'PASS'
        else:
            spec = importlib.util.spec_from_file_location('ytstack_package_tests', ROOT / 'tests/test_package.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.ROOT = root
            names = [CASES[args.case]] if args.case else list(CASES.values())
            suite = unittest.TestSuite(module.PackageTests(name) for name in names)
            result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
            receipt['cases'] = result.cases
            statuses = {case['status'] for case in result.cases}
            receipt['status'] = ('FAIL' if 'FAIL' in statuses else
                                 'BLOCKED' if 'BLOCKED' in statuses else
                                 'SKIPPED' if 'SKIPPED' in statuses else 'PASS')
        receipt['target_after'] = identity(root)
        receipt['target_unchanged'] = receipt['target_before'] == receipt['target_after']
        receipt['cleanup_passed'] = all(item['removed'] for case in receipt['cases'] for item in case['scratch'])
        if not receipt['target_unchanged'] or not receipt['cleanup_passed']:
            receipt['status'] = 'FAIL'
    except (OSError, subprocess.TimeoutExpired) as error:
        receipt.update(status='BLOCKED', error=str(error))
    except Exception:
        receipt.update(status='FAIL', error=traceback.format_exc())
    save(args.evidence, receipt)
    print(f"{receipt['status']}: {args.evidence}")
    return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2, 'SKIPPED': 3}[receipt['status']]


if __name__ == '__main__':
    sys.exit(main())
