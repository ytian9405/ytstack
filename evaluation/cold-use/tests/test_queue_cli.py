#!/usr/bin/env python3
"""Tiny Queue public CLI behavior tests; Python standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'queue_cli.py'
RECORDS = []


class Blocked(RuntimeError):
    pass


class QueueCases(unittest.TestCase):
    def setUp(self):
        self.record = {'id': self._testMethodName.split('_')[1],
                       'test': self._testMethodName, 'actions': [], 'assertions': []}
        RECORDS.append(self.record)
        self.scratch = tempfile.TemporaryDirectory(prefix='tiny-queue-test-')
        self.record['scratch'] = self.scratch.name
        self.addCleanup(self.clean)
        self.state = Path(self.scratch.name) / 'nested' / 'queue.json'

    def clean(self):
        self.scratch.cleanup()
        self.record['cleanup'] = {'scratch_removed': not Path(self.scratch.name).exists(),
                                  'background_processes_started': []}

    def expect(self, label, actual, expected):
        self.record['assertions'].append({'label': label, 'actual': actual,
                                          'expected': expected,
                                          'status': 'PASS' if actual == expected else 'FAIL'})
        self.assertEqual(actual, expected, label)

    def cli(self, *args, error=False):
        command = [sys.executable, str(TARGET), '--state', str(self.state), *args]
        action = {'command': shlex.join(command), 'cwd': str(ROOT)}
        self.record['actions'].append(action)
        try:
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                    timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:
            action['blocker'] = str(exc)
            raise Blocked(str(exc)) from exc
        action.update(stdout=result.stdout, stderr=result.stderr, exit_status=result.returncode)
        if error:
            self.expect('invalid input exits nonzero', result.returncode != 0, True)
            self.expect('invalid input reports an error on stderr', bool(result.stderr.strip()), True)
            return
        self.expect('CLI command exits zero', result.returncode, 0)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail('CLI must return JSON; stdout=' + repr(result.stdout))

    def test_TQ01_empty_queue(self):
        self.expect('nonexistent queue lists empty', self.cli('list'), [])
        self.expect('listing does not create state', self.state.exists(), False)

    def test_TQ02_add_persistence_order(self):
        first = {'id': 1, 'title': '  Prepare slides 雪  ', 'done': False}
        second = {'id': 2, 'title': 'Send notes', 'done': False}
        self.expect('first add returns ID 1 and exact title',
                    self.cli('add', '  Prepare slides 雪  '), first)
        self.expect('first mutation creates parent directory', self.state.parent.is_dir(), True)
        self.expect('fresh process sees first persisted task', self.cli('list'), [first])
        self.expect('next add returns increasing ID', self.cli('add', 'Send notes'), second)
        self.expect('fresh process preserves insertion order', self.cli('list'), [first, second])
        self.expect('disk state contains both exact tasks', json.loads(self.state.read_text()),
                    [first, second])

    def test_TQ03_complete_idempotence(self):
        self.expect('setup first task', self.cli('add', 'Prepare slides'),
                    {'id': 1, 'title': 'Prepare slides', 'done': False})
        self.expect('setup second task', self.cli('add', 'Send notes'),
                    {'id': 2, 'title': 'Send notes', 'done': False})
        completed = {'id': 1, 'title': 'Prepare slides', 'done': True}
        expected = [completed, {'id': 2, 'title': 'Send notes', 'done': False}]
        self.expect('completion preserves title and changes done', self.cli('complete', '1'), completed)
        self.expect('completion persists and preserves other task', self.cli('list'), expected)
        self.expect('repeat completion returns same task', self.cli('complete', '1'), completed)
        self.expect('repeat completion has no duplicate effects', self.cli('list'), expected)
        self.expect('IDs increase after completion', self.cli('add', 'Archive'),
                    {'id': 3, 'title': 'Archive', 'done': False})

    def test_TQ04_blank_title_rejected(self):
        self.cli('add', ' \t ', error=True)
        self.expect('rejected first write leaves state absent', self.state.exists(), False)
        self.expect('rejected first write leaves queue empty', self.cli('list'), [])
        original = {'id': 1, 'title': 'Keep me', 'done': False}
        self.expect('setup existing task', self.cli('add', 'Keep me'), original)
        before = json.loads(self.state.read_text())
        self.cli('add', '\n\t', error=True)
        self.expect('blank title does not change stored tasks', json.loads(self.state.read_text()), before)
        self.expect('fresh process sees unchanged tasks', self.cli('list'), [original])

    def test_TQ05_unknown_id_rejected(self):
        self.cli('complete', '42', error=True)
        self.expect('unknown ID leaves missing state absent', self.state.exists(), False)
        original = {'id': 1, 'title': 'Keep me', 'done': False}
        self.expect('setup existing task', self.cli('add', 'Keep me'), original)
        before = json.loads(self.state.read_text())
        self.cli('complete', '42', error=True)
        self.expect('unknown ID does not change stored tasks', json.loads(self.state.read_text()), before)
        self.expect('fresh process sees unchanged tasks', self.cli('list'), [original])


class EvidenceResult(unittest.TextTestResult):
    def addSuccess(self, test):
        test.record['status'] = 'PASS'
        super().addSuccess(test)

    def addFailure(self, test, err):
        test.record.update(status='FAIL', detail=self._exc_info_to_string(err, test))
        super().addFailure(test, err)

    def addError(self, test, err):
        test.record.update(status='BLOCKED' if issubclass(err[0], Blocked) else 'FAIL',
                           detail=self._exc_info_to_string(err, test))
        super().addError(test, err)


def doctor():
    if sys.version_info < (3, 8):
        raise Blocked('Python 3.8+ is required by this test runner')
    if not TARGET.is_file():
        raise Blocked('CLI missing: ' + str(TARGET))
    try:
        source = TARGET.read_bytes()
        compile(source, str(TARGET), 'exec')
        result = subprocess.run([sys.executable, str(TARGET), '--help'], cwd=ROOT,
                                capture_output=True, text=True, timeout=5)
    except (OSError, SyntaxError, subprocess.TimeoutExpired) as exc:
        raise Blocked(str(exc)) from exc
    if result.returncode != 0:
        raise Blocked('CLI --help could not start: ' + result.stderr)
    return {'python': sys.version, 'executable': sys.executable, 'target': str(TARGET),
            'sha256': hashlib.sha256(source).hexdigest(), 'help_exit_status': result.returncode,
            'help_stdout': result.stdout, 'help_stderr': result.stderr,
            'network': 'unused', 'credentials': 'not required', 'server': 'none'}


def main():
    global TARGET
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['TQ01', 'TQ02', 'TQ03', 'TQ04', 'TQ05'])
    parser.add_argument('--target', type=Path, default=TARGET,
                        help='Alternate isolated CLI copy; expectations stay unchanged')
    parser.add_argument('--evidence', type=Path, help='New receipt path outside disposable test state')
    parser.add_argument('--doctor', action='store_true', help='Read-only prerequisite check only')
    args = parser.parse_args()
    TARGET = args.target.resolve()
    if args.evidence and args.evidence.exists():
        parser.error('Evidence path already exists; choose a new path to preserve history')
    receipt = {'command': shlex.join([sys.executable, *sys.argv]), 'cwd': str(Path.cwd()),
               'cases': RECORDS}
    code = 0
    try:
        receipt['doctor'] = doctor()
        if args.doctor:
            receipt['status'] = 'PASS'
        else:
            names = [name for name in unittest.defaultTestLoader.getTestCaseNames(QueueCases)
                     if args.case is None or name.split('_')[1] == args.case]
            suite = unittest.TestSuite(QueueCases(name) for name in names)
            result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
            code = 2 if any(c['status'] == 'BLOCKED' for c in RECORDS) else (0 if result.wasSuccessful() else 1)
            receipt['status'] = {0: 'PASS', 1: 'FAIL', 2: 'BLOCKED'}[code]
    except Blocked as exc:
        receipt.update(status='BLOCKED', blocker=str(exc))
        code = 2
    except Exception:
        receipt.update(status='FAIL', runner_error=traceback.format_exc())
        code = 1
    receipt['exit_status'] = code
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
        print('Evidence:', args.evidence.resolve())
    else:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
