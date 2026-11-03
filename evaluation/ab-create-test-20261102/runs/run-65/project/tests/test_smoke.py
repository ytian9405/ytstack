import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class SmokeTests(unittest.TestCase):
    def test_empty_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / 'expense_cli.py'),
                 '--state', str(Path(directory) / 'state.json'), 'summary'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout),
                             {'count': 0, 'total_cents': 0, 'by_category': {}})


if __name__ == '__main__':
    unittest.main()
