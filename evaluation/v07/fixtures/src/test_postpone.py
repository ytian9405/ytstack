import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, state):
    return subprocess.run(
        [sys.executable, str(ROOT / 'queue_cli.py'), '--state', str(state), *args],
        capture_output=True, text=True, timeout=10)


class PostponeTests(unittest.TestCase):
    def test_postpone_command_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'queue.json'
            added = run(['add', '买电池'], state)
            self.assertEqual(added.returncode, 0, added.stderr)
            postponed = run(['postpone', '1'], state)
            self.assertEqual(postponed.returncode, 0, postponed.stderr)


if __name__ == '__main__':
    unittest.main()
