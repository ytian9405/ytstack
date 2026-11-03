#!/usr/bin/env python3
"""Extract the user's own messages from Codex session logs, for preference analysis.

Each kept message is paired with the assistant reply just before it, so an
analyst can see what the user was reacting to. Subagent threads, scheduled
automations, and evaluation sandboxes are dropped. Output goes outside the
repository by default because it contains private conversation text.

Logs written before Codex recorded turn_attribution have no trigger
information, so a turn counts as human typing when its session was started by
a desktop or CLI UI (source vscode/cli) instead of a subagent or exec run.

    python3 evaluation/prefs/mine.py --codex-home ~/.codex --out ~/.ytstack-prefs
"""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HUMAN_TRIGGERS = {'composer', 'user', 'edit_user_message', 'remote_android'}
UI_SOURCES = {'vscode', 'cli'}  # sessions started from a human UI; exec/subagent are not
INJECTED = re.compile(r'^\s*<|<environment_context>|AGENTS\.md instructions|<codex_delegation>|<user_instructions>|^# Context from my IDE')
SANDBOX_CWD = re.compile(r'/tmp/|ytjudge|ytgrade|ytdiag|ytprobe|ytev|ytmut')
NODE_UNZSTD = "const z=require('zlib'),f=require('fs');f.writeFileSync(process.argv[2],z.zstdDecompressSync(f.readFileSync(process.argv[1])))"


def decompress(src, dst):
    try:
        import zstandard
        dst.write_bytes(zstandard.ZstdDecompressor().decompressobj().decompress(src.read_bytes()))
    except ImportError:
        subprocess.run(['node', '-e', NODE_UNZSTD, str(src), str(dst)], check=True)


def rollouts(codex_home, scratch):
    for folder in ['sessions', 'archived_sessions']:
        for path in sorted((codex_home / folder).rglob('*')):
            if path.name.endswith('.jsonl'):
                yield path
            elif path.name.endswith('.jsonl.zst'):
                plain = scratch / path.name[:-4]
                decompress(path, plain)
                yield plain
                plain.unlink()  # decompressed logs can be ~4x larger; don't keep them all


def human_turns(path):
    cwd, subagent, ui_source, human, reply, turns = None, False, False, False, '', []
    for line in path.open(errors='ignore'):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        payload = event.get('payload') or {}
        kind = event.get('type')
        if kind == 'session_meta':
            cwd = payload.get('cwd')
            source = payload.get('source')
            subagent = isinstance(source, dict) and 'subagent' in source
            ui_source = not subagent and isinstance(source, str) and source in UI_SOURCES
        elif kind == 'turn_context':
            cwd = cwd or payload.get('cwd')
        elif kind == 'event_msg' and payload.get('type') == 'task_started':
            attribution = payload.get('turn_attribution')
            # Old logs carry no turn_attribution: trust the turn as human when
            # the session came from a UI, otherwise fall back to not human.
            human = (attribution or {}).get('turn_trigger') in HUMAN_TRIGGERS if attribution is not None else ui_source
        elif kind == 'response_item' and payload.get('type') == 'message':
            text = ''.join(c.get('text', '') for c in payload.get('content', []) if isinstance(c, dict))
            if payload.get('role') == 'assistant' and text.strip():
                reply = text
            elif payload.get('role') == 'user' and human and text.strip() and not INJECTED.search(text[:400]):
                turns.append({'before': reply[-2500:], 'user': text[:3000]})
    if subagent or (cwd and SANDBOX_CWD.search(cwd)):
        return cwd, []
    return cwd, turns


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--codex-home', type=Path, action='append', required=True, help='Repeat for several Codex homes.')
    parser.add_argument('--out', type=Path, default=Path.home() / '.ytstack-prefs')
    parser.add_argument('--slices', type=int, default=3, help='Split chronologically so patterns can be cross-checked.')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix='ytprefs-') as scratch:
        for home in args.codex_home:
            for path in rollouts(home.expanduser(), Path(scratch)):
                cwd, turns = human_turns(path)
                date = (re.search(r'\d{4}-\d{2}-\d{2}', path.name) or [''])[0]
                project = (cwd or '?').rstrip('/').split('/')[-1]
                rows += [(date, path.name, i, project, t) for i, t in enumerate(turns)]
    rows.sort(key=lambda r: r[:3])
    size = -(-len(rows) // args.slices) if rows else 0
    for s in range(args.slices):
        part = rows[s * size:(s + 1) * size]
        text = []
        for n, (date, _, _, project, turn) in enumerate(part, 1):
            before = turn['before'].strip()
            if len(before) > 1200:
                before = before[:700] + ' …… ' + before[-500:]
            text.append(f"### 第{s + 1}段-{n} | {date} | 项目 {project}\n[AI 上一条回复]\n{before or '（会话开头）'}\n[用户]\n{turn['user'].strip()}\n")
        (args.out / f'slice{s + 1}.md').write_text('\n'.join(text))
    shutil.copy2(Path(__file__).with_name('prompt.md'), args.out / 'prompt.md')
    print(json.dumps({'human_messages': len(rows), 'slices': args.slices, 'out': str(args.out),
                      'first': rows[0][0] if rows else None, 'last': rows[-1][0] if rows else None}, ensure_ascii=False))


if __name__ == '__main__':
    main()
