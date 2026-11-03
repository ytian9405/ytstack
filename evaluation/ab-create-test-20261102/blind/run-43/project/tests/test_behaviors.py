"""Contract tests through the real CLI; all state belongs to each test."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class LedgerBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='ledger-test-')
        self.addCleanup(self.scratch.cleanup)
        self.state = Path(self.scratch.name) / 'nested' / 'ledger.json'
        self.cli = Path(__file__).resolve().parents[1] / 'expense_cli.py'

    def invoke(self, *args, valid=True):
        result = subprocess.run([sys.executable, str(self.cli), '--state', str(self.state), *args],
                                capture_output=True, text=True, timeout=10)
        if valid:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip(), 'invalid input must explain error on stderr')

    def add(self, title='午餐', cents='1250', category='food'):
        return self.invoke('add', title, '--cents', cents, '--category', category)

    def test_LL01_empty_reads_do_not_write(self):
        self.assertEqual(self.invoke('list'), [])
        self.assertEqual(self.invoke('summary'), {'count': 0, 'total_cents': 0, 'by_category': {}})
        self.assertFalse(self.state.exists())
        self.assertFalse(self.state.parent.exists())

    def test_LL02_add_preserves_strings_and_persists(self):
        first = {'id': 1, 'title': ' 午餐 🍜 ', 'cents': 1250, 'category': ' 餐饮 ', 'voided': False}
        second = {'id': 2, 'title': '车票', 'cents': 300, 'category': 'travel', 'voided': False}
        self.assertEqual(self.add(' 午餐 🍜 ', category=' 餐饮 '), first)
        self.assertEqual(self.invoke('list'), [first])
        self.assertTrue(self.state.is_file())
        self.assertEqual(self.add('车票', '300', 'travel'), second)
        self.assertEqual(self.invoke('list'), [first, second])

    def test_LL03_void_is_persistent_idempotent_and_ids_increase(self):
        self.add()
        voided = {'id': 1, 'title': '午餐', 'cents': 1250, 'category': 'food', 'voided': True}
        self.assertEqual(self.invoke('void', '1'), voided)
        self.assertEqual(self.invoke('list'), [voided])
        before = self.state.read_bytes()
        self.assertEqual(self.invoke('void', '1'), voided)
        self.assertEqual(self.state.read_bytes(), before)
        second = {'id': 2, 'title': '茶', 'cents': 200, 'category': 'food', 'voided': False}
        self.assertEqual(self.add('茶', '200'), second)
        self.assertEqual(self.invoke('list'), [voided, second])

    def test_LL04_summary_groups_only_active_entries(self):
        self.add()
        self.add('茶', '200')
        self.add('车票', '300', 'travel')
        self.assertEqual(self.invoke('summary'), {'count': 3, 'total_cents': 1750,
                                                'by_category': {'food': 1450, 'travel': 300}})
        self.invoke('void', '1')
        self.assertEqual(self.invoke('summary'), {'count': 2, 'total_cents': 500,
                                                'by_category': {'food': 200, 'travel': 300}})
        self.invoke('void', '2')
        self.invoke('void', '3')
        self.assertEqual(self.invoke('summary'), {'count': 0, 'total_cents': 0, 'by_category': {}})

    def test_LL05_rejected_changes_preserve_data(self):
        self.add()
        expected = [{'id': 1, 'title': '午餐', 'cents': 1250, 'category': 'food', 'voided': False}]
        before = self.state.read_bytes()
        commands = [
            ('add', 'bad', '--cents', value, '--category', 'food')
            for value in ('0', '-1', '1.5', 'abc')
        ] + [('add', ' \t ', '--cents', '10', '--category', 'food'),
             ('add', 'bad', '--cents', '10', '--category', ' \t '), ('void', '999')]
        for args in commands:
            with self.subTest(args=args):
                self.invoke(*args, valid=False)
                self.assertEqual(self.state.read_bytes(), before)
                self.assertEqual(self.invoke('list'), expected)


if __name__ == '__main__':
    unittest.main()
