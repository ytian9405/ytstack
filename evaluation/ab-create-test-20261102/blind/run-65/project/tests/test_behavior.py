"""Public CLI contract tests; each invocation is a fresh process."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(os.environ.get('LEDGER_TEST_CLI', Path(__file__).resolve().parents[1] / 'expense_cli.py')).resolve()


class LedgerBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ledger-test-')
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'nested' / 'ledger.json'

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(CLI), '--state', str(self.state), *args],
                              capture_output=True, text=True, encoding='utf-8', timeout=10)

    def success(self, *args):
        result = self.invoke(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)  # Also rejects multiple JSON values or trailing output.

    def add(self, title='午餐', cents='1250', category='food'):
        return self.success('add', title, '--cents', cents, '--category', category)

    def test_C01_missing_state_reads_do_not_write(self):
        self.assertEqual(self.success('list'), [])
        self.assertEqual(self.success('summary'), {'count': 0, 'total_cents': 0, 'by_category': {}})
        self.assertFalse(self.state.exists())
        self.assertFalse(self.state.parent.exists())

    def test_C02_add_preserves_strings_and_persists_in_order(self):
        first = {'id': 1, 'title': '  午餐 🍜  ', 'cents': 1,
                 'category': ' 食物 🥢 ', 'voided': False}
        second = {'id': 2, 'title': '交通', 'cents': 250, 'category': 'travel', 'voided': False}
        self.assertEqual(self.add(first['title'], '1', first['category']), first)
        self.assertTrue(self.state.is_file())
        self.assertEqual(self.add('交通', '250', 'travel'), second)
        self.assertEqual(self.success('list'), [first, second])

    def test_C03_void_is_persistent_idempotent_and_ids_not_reused(self):
        first = self.add()
        second = self.add('车票', '300', 'travel')
        expected = dict(second, voided=True)
        self.assertEqual(self.success('void', '2'), expected)
        self.assertEqual(self.success('list'), [first, expected])
        before = self.state.read_bytes()
        self.assertEqual(self.success('void', '2'), expected)
        self.assertEqual(self.state.read_bytes(), before)
        third = self.add('晚餐', '500', 'food')
        self.assertEqual(third, {'id': 3, 'title': '晚餐', 'cents': 500, 'category': 'food', 'voided': False})
        self.assertEqual(self.success('list'), [first, expected, third])

    def test_C04_summary_aggregates_only_active_entries(self):
        self.add('a', '101', 'food')
        self.add('b', '202', 'food')
        self.add('c', '17', 'travel')
        self.add('d', '999', 'removed')
        self.success('void', '2')
        self.success('void', '4')
        self.assertEqual(self.success('summary'), {'count': 2, 'total_cents': 118,
                                                  'by_category': {'food': 101, 'travel': 17}})
        self.success('void', '1')
        self.success('void', '3')
        self.assertEqual(self.success('summary'), {'count': 0, 'total_cents': 0, 'by_category': {}})

    def test_C05_summary_sums_repeated_categories(self):
        self.add('a', '101', 'food')
        self.add('b', '202', 'food')
        self.add('c', '17', ' Food ')
        self.assertEqual(self.success('summary'), {'count': 3, 'total_cents': 320,
                                                  'by_category': {'food': 303, ' Food ': 17}})

    def test_C06_invalid_commands_preserve_existing_bytes(self):
        entry = self.add()
        invalid = [
            ('add', 'a', '--cents', amount, '--category', 'food')
            for amount in ('0', '-1', '1.5', 'abc')
        ] + [
            ('add', title, '--cents', '1', '--category', category)
            for title, category in (('', 'food'), (' \t\n', 'food'), ('a', ''), ('a', ' \t\n'))
        ] + [('void', '999'), ('void', '0'), ('void', '-1')]
        for args in invalid:
            with self.subTest(args=args):
                before = self.state.read_bytes()
                result = self.invoke(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertEqual(self.state.read_bytes(), before)
                self.assertEqual(self.success('list'), [entry])
        self.assertEqual(self.add('next')['id'], 2)

    def test_C07_invalid_commands_do_not_create_missing_state(self):
        for args in [('add', 'a', '--cents', '0', '--category', 'food'), ('void', '1')]:
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
