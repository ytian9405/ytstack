import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def test_bundle_command_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'queue.json'
            added = subprocess.run(
                [sys.executable, str(ROOT / 'queue_cli.py'), '--state', str(state), 'add', '买电池'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(added.returncode, 0, added.stderr)
            linked = subprocess.run(
                [sys.executable, str(ROOT / 'queue_cli.py'), '--state', str(state),
                 'bundle', '1', '1'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(linked.returncode, 0, linked.stderr)


if __name__ == '__main__':
    unittest.main()
