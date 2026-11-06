import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = str(Path(__file__).resolve().parents[1] / 'temp_log.py')


class SmokeTests(unittest.TestCase):
    def test_add_and_stats(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / 'logger.json'
            config.write_text(json.dumps({'sensors': {'S1': '阳台'}}, ensure_ascii=False))
            state = home / 'state.json'
            done = subprocess.run(
                [sys.executable, CLI, '--state', str(state), '--config', str(config),
                 'add', 'S1', '21.5'], capture_output=True, text=True, timeout=10)
            self.assertEqual(done.returncode, 0, done.stderr)
            picked = subprocess.run(
                [sys.executable, CLI, '--state', str(state), '--config', str(config),
                 'stats', '--sensor', 'S1'], capture_output=True, text=True, timeout=10)
            self.assertEqual(json.loads(picked.stdout)['count'], 1)

    def test_unknown_sensor_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [sys.executable, CLI, '--state', str(home / 'state.json'),
                 '--config', str(home / 'logger.json'), 'add', 'S9', '21.5'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn('unknown sensor id', result.stderr)


if __name__ == '__main__':
    unittest.main()
