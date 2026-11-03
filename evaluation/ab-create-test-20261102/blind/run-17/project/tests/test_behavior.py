"""Public CLI contract checks; each invocation is a new process."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LedgerBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ledger-test-')
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name) / 'nested' / 'ledger.json'

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / 'expense_cli.py'), '--state', str(self.state),
             *map(str, args)], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', timeout=10)

    def ok(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        # json.loads also rejects trailing values, enforcing one JSON value.
        return json.loads(result.stdout)

    def add(self, title='午餐', cents=1250, category='food'):
        return self.ok('add', title, '--cents', cents, '--category', category)

    def test_LL01_missing_state_reads_do_not_create_file(self):
        self.assertEqual(self.ok('list'), [])
        self.assertFalse(self.state.exists())
        self.assertEqual(self.ok('summary'),
                         {'count': 0, 'total_cents': 0, 'by_category': {}})
        self.assertFalse(self.state.exists())

    def test_LL02_add_preserves_strings_and_persists_in_order(self):
        first = {'id': 1, 'title': '  午餐 🍜  ', 'cents': 1,
                 'category': ' 餐饮 ☕ ', 'voided': False}
        second = {'id': 2, 'title': '车票', 'cents': 987654321,
                  'category': '交通', 'voided': False}
        self.assertEqual(self.add(first['title'], first['cents'], first['category']), first)
        self.assertTrue(self.state.is_file())
        self.assertEqual(self.add(second['title'], second['cents'], second['category']), second)
        self.assertEqual(self.ok('list'), [first, second])

    def test_LL03_void_is_persistent_idempotent_and_ids_are_not_reused(self):
        first = self.add('  早餐 ', 300, ' food ')
        second = self.add('午餐', 900, 'food')
        expected = dict(second, voided=True)
        self.assertEqual(self.ok('void', 2), expected)
        self.assertEqual(self.ok('list'), [first, expected])
        before = self.state.read_bytes()
        self.assertEqual(self.ok('void', 2), expected)
        self.assertEqual(self.state.read_bytes(), before)
        third = {'id': 3, 'title': '晚餐', 'cents': 500,
                 'category': 'food', 'voided': False}
        self.assertEqual(self.add('晚餐', 500), third)
        self.assertEqual(self.ok('list'), [first, expected, third])

    def test_LL04_summary_groups_only_active_records(self):
        self.add('早餐', 100, 'food')
        self.add('午餐', 250, 'food')
        self.add('公交', 75, '交通')
        self.add('退单', 999, 'refund-only')
        self.add('空格类别', 20, ' food ')
        self.ok('void', 4)
        self.assertEqual(self.ok('summary'), {
            'count': 4, 'total_cents': 445,
            'by_category': {'food': 350, '交通': 75, ' food ': 20}})
        for entry_id in (1, 2, 3, 5):
            self.ok('void', entry_id)
        self.assertEqual(self.ok('summary'),
                         {'count': 0, 'total_cents': 0, 'by_category': {}})
        self.assertEqual(len(self.ok('list')), 5)

    def test_LL05_invalid_adds_preserve_existing_data(self):
        record = self.add()
        before = self.state.read_bytes()
        cases = [
            ('zero', '午餐', '0', 'food'),
            ('negative', '午餐', '-1', 'food'),
            ('decimal', '午餐', '1.5', 'food'),
            ('text', '午餐', 'abc', 'food'),
            ('blank_title', '', '10', 'food'),
            ('whitespace_title', ' \t\n\u3000', '10', 'food'),
            ('blank_category', '午餐', '10', ''),
            ('whitespace_category', '午餐', '10', ' \t\n\u3000'),
        ]
        for label, title, cents, category in cases:
            with self.subTest(case=label):
                result = self.run_cli('add', title, '--cents', cents, '--category', category)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertEqual(self.state.read_bytes(), before)
                self.assertEqual(self.ok('list'), [record])
        self.assertEqual(self.add('有效', 10)['id'], 2)

    def test_LL06_unknown_void_preserves_existing_data(self):
        record = self.add()
        before = self.state.read_bytes()
        for entry_id in (0, -1, 2, 999):
            with self.subTest(entry_id=entry_id):
                result = self.run_cli('void', entry_id)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertEqual(self.state.read_bytes(), before)
                self.assertEqual(self.ok('list'), [record])

    def test_LL07_failed_writes_on_missing_state_do_not_create_it(self):
        for args in [('add', 'x', '--cents', '0', '--category', 'food'), ('void', '1')]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
