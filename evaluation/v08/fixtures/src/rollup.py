#!/usr/bin/env python3
"""Keep reading data/month-lines.jsonl until jobs/rollup-stop exists."""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'month-lines.jsonl'
JOBS = Path(__file__).resolve().parent
PROGRESS = JOBS / 'rollup-progress.json'
PID = JOBS / 'rollup.pid'
STOP = JOBS / 'rollup-stop'


def main():
    lines = [line for line in SRC.read_text().splitlines() if line.strip()]
    PID.write_text(str(os.getpid()) + '\n')
    pause = float(os.environ.get('ROLLUP_PAUSE', '30'))
    tick = 0
    while not STOP.exists():
        tick += 1
        PROGRESS.write_text(json.dumps({
            'done': False,
            'tick': tick,
            'lines': len(lines),
        }, ensure_ascii=False) + '\n')
        time.sleep(pause)
    PROGRESS.write_text(json.dumps({
        'done': True,
        'tick': tick,
        'lines': len(lines),
    }, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
