"""Evaluator-only literal contract checks, separate from generated tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def check_target(target):
    actions = []
    with tempfile.TemporaryDirectory(prefix='ledger-oracle-') as directory:
        state = Path(directory) / 'nested/state.json'

        def call(*args, okay=True):
            command = [sys.executable, str(target), '--state', str(state), *args]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            actions.append({'command': command, 'exit_status': result.returncode,
                            'stdout': result.stdout, 'stderr': result.stderr})
            if okay:
                assert result.returncode == 0, result.stderr
                return json.loads(result.stdout)
            assert result.returncode != 0 and result.stderr, 'Invalid input was accepted'

        try:
            assert call('list') == []
            assert not state.exists()
            expected = [
                {'id': 1, 'title': '  午餐 雪  ', 'cents': 1250, 'category': 'food', 'voided': False},
                {'id': 2, 'title': 'coffee', 'cents': 350, 'category': 'food', 'voided': False},
                {'id': 3, 'title': 'book', 'cents': 900, 'category': 'books', 'voided': False},
            ]
            for item in expected:
                assert call('add', item['title'], '--cents', str(item['cents']), '--category', item['category']) == item
            assert call('list') == expected, 'Persisted records differ'
            assert call('summary') == {'count': 3, 'total_cents': 2500, 'by_category': {'food': 1600, 'books': 900}}, 'Category accumulation differs'
            expected[1]['voided'] = True
            assert call('void', '2') == expected[1], 'Void did not change the record'
            assert call('void', '2') == expected[1]
            assert call('list') == expected
            assert call('summary') == {'count': 2, 'total_cents': 2150, 'by_category': {'food': 1250, 'books': 900}}, 'Voided records included'
            for title, cents, category in [('bad', '0', 'food'), ('  ', '10', 'food'), ('bad', '-1', 'food'), ('bad', '1.5', 'food'), ('bad', 'x', 'food'), ('bad', '10', '  ')]:
                call('add', title, '--cents', cents, '--category', category, okay=False)
                assert call('list') == expected, 'Invalid input changed persisted records'
            call('void', '999', okay=False)
            assert call('list') == expected
            fourth = {'id': 4, 'title': 'taxi', 'cents': 200, 'category': ' travel 雪 ', 'voided': False}
            assert call('add', 'taxi', '--cents', '200', '--category', ' travel 雪 ') == fourth
            for id in ['1', '3', '4']:
                call('void', id)
            assert call('summary') == {'count': 0, 'total_cents': 0, 'by_category': {}}
            return {'status': 'PASS', 'actions': actions}
        except (AssertionError, json.JSONDecodeError) as error:
            return {'status': 'FAIL', 'reason': str(error), 'actions': actions}
