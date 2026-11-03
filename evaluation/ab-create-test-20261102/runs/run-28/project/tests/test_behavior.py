"""Public CLI contracts; every invocation is a new process with owned state."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'expense_cli.py'


class LedgerBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='ledger-behavior-', dir=ROOT)
        self.addCleanup(self.scratch.cleanup)
        self.state = Path(self.scratch.name) / 'nested' / 'ledger.json'

    def invoke(self, *args, success=True):
        command = [sys.executable, str(CLI), '--state', str(self.state), *args]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if os.environ.get('LEDGER_TRACE'):
            print(json.dumps({'case': self.id(), 'command': command,
                              'stdout': result.stdout, 'stderr': result.stderr,
                              'exit_code': result.returncode}, ensure_ascii=False), flush=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip())

    def add(self, title='午餐', cents='1250', category='food'):
        return self.invoke('add', title, '--cents', cents, '--category', category)

    def test_LL01_empty_reads(self):
        self.assertEqual(self.invoke('list'), [])
        self.assertEqual(self.invoke('summary'),
                         {'count': 0, 'total_cents': 0, 'by_category': {}})
        self.assertFalse(self.state.exists())
        self.assertFalse(self.state.parent.exists())

    def test_LL02_add_persistence(self):
        first = {'id': 1, 'title': ' 午餐 🍜 ', 'cents': 1250,
                 'category': ' 餐饮 ', 'voided': False}
        second = {'id': 2, 'title': '车票', 'cents': 300,
                  'category': 'travel', 'voided': False}
        self.assertEqual(self.add(' 午餐 🍜 ', category=' 餐饮 '), first)
        self.assertTrue(self.state.is_file())
        self.assertEqual(self.invoke('list'), [first])
        self.assertEqual(self.add('车票', '300', 'travel'), second)
        self.assertEqual(self.invoke('list'), [first, second])

    def test_LL03_void_and_ids(self):
        original = {'id': 1, 'title': '午餐', 'cents': 1250,
                    'category': 'food', 'voided': False}
        self.assertEqual(self.add(), original)
        voided = dict(original, voided=True)
        self.assertEqual(self.invoke('void', '1'), voided)
        self.assertEqual(self.invoke('list'), [voided])
        snapshot = self.state.read_bytes()
        self.assertEqual(self.invoke('void', '1'), voided)
        self.assertEqual(self.state.read_bytes(), snapshot)
        second = {'id': 2, 'title': '晚餐', 'cents': 900,
                  'category': 'food', 'voided': False}
        self.assertEqual(self.add('晚餐', '900'), second)
        self.assertEqual(self.invoke('list'), [voided, second])

    def test_LL04_summary(self):
        self.add('午餐', '1250')
        self.add('晚餐', '750')
        self.add('车票', '300', 'travel')
        self.add('退款前记录', '999', 'void-only')
        self.invoke('void', '4')
        self.assertEqual(self.invoke('summary'),
                         {'count': 3, 'total_cents': 2300,
                          'by_category': {'food': 2000, 'travel': 300}})
        for entry_id in ('1', '2', '3'):
            self.invoke('void', entry_id)
        self.assertEqual(self.invoke('summary'),
                         {'count': 0, 'total_cents': 0, 'by_category': {}})

    def test_LL05_invalid_inputs_preserve_data(self):
        expected = {'id': 1, 'title': '午餐', 'cents': 1250,
                    'category': 'food', 'voided': False}
        self.assertEqual(self.add(), expected)
        snapshot = self.state.read_bytes()
        invalid = [
            ('add', 'x', '--cents', value, '--category', 'food')
            for value in ('0', '-1', '1.5', 'abc')
        ] + [('add', ' \t', '--cents', '100', '--category', 'food'),
             ('add', 'x', '--cents', '100', '--category', ' \t'),
             ('void', '999')]
        for args in invalid:
            with self.subTest(args=args):
                self.invoke(*args, success=False)
                self.assertEqual(self.state.read_bytes(), snapshot)
                self.assertEqual(self.invoke('list'), [expected])


if __name__ == '__main__':
    unittest.main()
