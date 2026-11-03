#!/usr/bin/env python3
"""Extract the user's own messages from Claude Code, pi, Cursor, and Trae logs.

Same pairing convention as mine.py: every kept user message is stored with the
assistant reply just before it, so an analyst sees what the user was reacting
to. Rows land in ~/.ytstack-prefs/other/rows.jsonl (one JSON object per line)
and hold private conversation text, so they must stay outside the repository.

    python3 evaluation/prefs/mine_other.py

Only the Python 3.9 standard library is used. Sources whose chats cannot be
read (Trae keeps conversations in an encrypted database) contribute nothing
and are reported with a note instead.
"""
import argparse
import json
import re
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Whole sessions dispatched by Orca are worker runs, not the user typing.
ORCA_TRIGGERS = (
    'You are working inside Orca',
    'You have 1 orchestration message',
    'You have 1 new orchestration message',
    'Please carry out this task from my Orca',
    'Coordinator checkpoint',
    'Reply with the single word OK',  # Orca terminal health-check probe
)
# The current Orca coordinator session in Claude Code lives here; skip it.
SKIP_CLAUDE_SESSIONS = set()  # filled from --skip-session (e.g. the session running this analysis)
PASTE_TAG = re.compile(r'</?pasted_content id="[^"]*">')
TIMESTAMP_TAG = re.compile(r'^<timestamp>.*?</timestamp>\s*', re.S)
QUERY_TAG = re.compile(r'</?user_query>')


def project_of(path):
    return ((path or '?').rstrip('/').split('/')[-1]) or '?'


def ms_date(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
    except (TypeError, ValueError, OSError):
        return '?'


def text_of_content(content):
    """Join the text parts of a message content (string or block list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(part.get('text', '') for part in content
                       if isinstance(part, dict) and part.get('type') == 'text')
    return ''


def clean_user_text(text):
    """Strip wrappers; return user text to keep, or None for injected noise."""
    text = (text or '').strip()
    for _ in range(3):
        if not text.startswith('<'):
            break
        if PASTE_TAG.match(text):
            text = PASTE_TAG.sub('', text).strip()  # user pasted text into the prompt
        else:
            return None  # <environment_context>, <user_info>, tool output, ...
    if not text or text.lstrip().startswith(ORCA_TRIGGERS):
        return None
    return text


def new_stats():
    return {'messages': 0, 'sessions': 0, 'by_month': defaultdict(int), 'dropped': defaultdict(int)}


def finish_rows(rows, stats, source):
    for row in rows:
        stats['by_month'][row['date'][:7]] += 1
        stats['messages'] += 1
        row['source'] = source
    stats['by_month'] = dict(sorted(stats['by_month'].items()))
    stats['dropped'] = dict(sorted(stats['dropped'].items()))
    return rows


# ---------------------------------------------------------------- Claude Code

def mine_claude(home, stats):
    """type=user with origin.kind=human is the user typing; skip subagent
    files, the Orca coordinator session, meta/compact summaries, and text
    that is system injection (leading '<' except pasted_content wrappers)."""
    rows = []
    for path in sorted((home / '.claude' / 'projects').glob('*/*.jsonl')):
        if 'subagents' in path.parts:
            stats['dropped']['subagent_files'] += 1
            continue
        session_rows, reply, cwd = [], '', None
        coordinator = False
        for line in path.open(errors='ignore'):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get('type')
            if kind not in ('user', 'assistant'):
                continue
            if event.get('sessionId') in SKIP_CLAUDE_SESSIONS:
                coordinator = True
                break
            if event.get('isSidechain'):
                continue
            cwd = cwd or event.get('cwd')
            text = text_of_content(event.get('message', {}).get('content'))
            if kind == 'assistant':
                if text.strip():
                    reply = text
                continue
            origin = event.get('origin')
            if not (isinstance(origin, dict) and origin.get('kind') == 'human'):
                stats['dropped']['not_human_origin'] += 1
                continue
            if event.get('isMeta') or event.get('isCompactSummary'):
                stats['dropped']['meta_or_compact'] += 1
                continue
            kept = clean_user_text(text)
            if kept is None:
                stats['dropped']['injected_or_empty'] += 1
                continue
            session_rows.append({'date': (event.get('timestamp') or '?')[:10],
                                 'session': event.get('sessionId') or path.stem,
                                 'before': reply[-2500:], 'user': kept[:3000]})
        if coordinator:
            stats['dropped']['coordinator_session'] += 1
            continue
        stats['sessions'] += 1
        project = project_of(cwd)
        for idx, row in enumerate(session_rows):
            row['idx'] = idx
            row['project'] = project
        rows += session_rows
    return finish_rows(rows, stats, 'claude-code')


# ------------------------------------------------------------------------- pi

def mine_pi(home, stats):
    """Sessions start with a type=session line (cwd, id); user/assistant
    messages follow as type=message. Sessions containing Orca dispatch
    briefs are dropped whole."""
    rows = []
    for path in sorted((home / '.pi' / 'agent' / 'sessions').glob('*/*.jsonl')):
        session_rows, reply, cwd, session = [], '', None, path.stem
        orca = False
        for line in path.open(errors='ignore'):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get('type')
            if kind == 'session':
                cwd = event.get('cwd')
                session = event.get('id') or session
                continue
            if kind != 'message':
                continue
            message = event.get('message') or {}
            role = message.get('role')
            if role not in ('user', 'assistant'):
                continue
            text = text_of_content(message.get('content'))
            if role == 'assistant':
                if text.strip():
                    reply = text
                continue
            if text.lstrip().startswith(ORCA_TRIGGERS):
                orca = True
                break
            kept = clean_user_text(text)
            if kept is None:
                stats['dropped']['injected_or_empty'] += 1
                continue
            session_rows.append({'date': (event.get('timestamp') or '?')[:10],
                                 'session': session,
                                 'before': reply[-2500:], 'user': kept[:3000]})
        if orca:
            stats['dropped']['orca_worker_sessions'] += 1
            continue
        stats['sessions'] += 1
        project = project_of(cwd)
        for idx, row in enumerate(session_rows):
            row['idx'] = idx
            row['project'] = project
        rows += session_rows
    return finish_rows(rows, stats, 'pi')


# ------------------------------------------------------------- Cursor editor

def mine_cursor_editor(db_path, stats):
    """state.vscdb: composerData:<id> holds fullConversationHeadersOnly (the
    message order); bubbleId:<composer>:<bubble> rows carry text, type
    1=user / 2=AI. Project comes from trackedGitRepos when present."""
    rows = []
    db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    try:
        cur = db.cursor()
        composers = cur.execute(
            "SELECT value FROM cursorDiskKV WHERE key LIKE 'composerData:%'").fetchall()
        for (value,) in composers:
            try:
                data = json.loads(value)
            except ValueError:
                continue
            headers = data.get('fullConversationHeadersOnly') or []
            if not headers or data.get('isBestOfNSubcomposer'):
                stats['dropped']['composers_without_conversation'] += 1
                continue
            stats['sessions'] += 1
            cid = data.get('composerId') or '?'
            repos = data.get('trackedGitRepos') or []
            project = project_of(repos[0].get('repoPath')) if repos else '?'
            created = data.get('createdAt')
            session_rows, reply = [], ''
            for header in headers:
                bubble_type = header.get('type')
                hit = cur.execute('SELECT value FROM cursorDiskKV WHERE key=?',
                                  (f'bubbleId:{cid}:{header.get("bubbleId")}',)).fetchone()
                if not hit:
                    stats['dropped']['missing_bubbles'] += 1
                    continue
                try:
                    bubble = json.loads(hit[0])
                except ValueError:
                    continue
                text = bubble.get('text') or ''
                if bubble_type == 2:
                    if text.strip():
                        reply = text
                    continue
                if bubble_type != 1:
                    stats['dropped']['other_bubble_types'] += 1
                    continue
                kept = clean_user_text(text)
                if kept is None:
                    stats['dropped']['injected_or_empty'] += 1
                    continue
                date = (bubble.get('createdAt') or ms_date(created))[:10]
                session_rows.append({'date': date, 'session': cid,
                                     'before': reply[-2500:], 'user': kept[:3000]})
            for idx, row in enumerate(session_rows):
                row['idx'] = idx
                row['project'] = project
            rows += session_rows
    finally:
        db.close()
    return finish_rows(rows, stats, 'cursor-editor')


# -------------------------------------------------------------- Cursor CLI

def read_cli_messages(db_path, stats):
    """store.db (blobs table) keeps one message per row as JSON next to
    protobuf chain copies; the JSON rows in rowid order are the conversation.
    The WAL can hold the newest rows, so copy db+wal to a temp dir first."""
    messages, proto_only = [], 0
    with tempfile.TemporaryDirectory(prefix='cursor-cli-') as tmp:
        for suffix in ('', '-wal', '-shm'):
            src = Path(str(db_path) + suffix)
            if src.exists():
                shutil.copy2(src, Path(tmp) / ('store.db' + suffix))
        db = sqlite3.connect(str(Path(tmp) / 'store.db'))
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'blobs' not in tables:
                return []
            for (blob,) in db.execute('SELECT data FROM blobs ORDER BY rowid'):
                try:
                    message = json.loads(blob)
                except ValueError:
                    proto_only += 1  # protobuf chain copy of a message
                    continue
                role = message.get('role')
                if role in ('user', 'assistant'):
                    messages.append((role, text_of_content(message.get('content'))))
        finally:
            db.close()
    if proto_only:
        stats['dropped']['protobuf_chain_blobs'] += proto_only
    return messages


def mine_cursor_cli(home, stats):
    """~/.cursor/chats/<workspace>/<chat>/: meta.json has cwd + createdAtMs;
    user text arrives wrapped in <timestamp>/<user_query> tags, which get
    unwrapped before the usual injection filter. Orca dispatch briefs are
    dropped by the Orca trigger check."""
    rows = []
    for meta_path in sorted((home / '.cursor' / 'chats').glob('*/*/meta.json')):
        try:
            meta = json.loads(meta_path.read_text())
        except ValueError:
            meta = {}
        stats['sessions'] += 1
        date = ms_date(meta.get('createdAtMs'))
        project = project_of(meta.get('cwd'))
        session_rows, reply = [], ''
        for role, text in read_cli_messages(meta_path.parent / 'store.db', stats):
            if role == 'assistant':
                if text.strip():
                    reply = text
                continue
            text = QUERY_TAG.sub('', TIMESTAMP_TAG.sub('', (text or '').strip())).strip()
            kept = clean_user_text(text)
            if kept is None:
                stats['dropped']['injected_or_dispatched'] += 1
                continue
            session_rows.append({'date': date, 'session': meta_path.parent.name,
                                 'before': reply[-2500:], 'user': kept[:3000]})
        for idx, row in enumerate(session_rows):
            row['idx'] = idx
            row['project'] = project
        rows += session_rows
    return finish_rows(rows, stats, 'cursor-cli')


# --------------------------------------------------------------------- Trae

def check_trae(home, stats):
    """Trae keeps conversations in ModularData/ai-agent/database.db, which is
    SQLCipher-encrypted (the file header is not SQLite), so there is nothing
    readable to mine; report 0 instead."""
    for name in ('Trae', 'Trae CN'):
        base = home / 'Library' / 'Application Support' / name
        db = base / 'ModularData' / 'ai-agent' / 'database.db'
        if db.exists():
            header = db.read_bytes()[:4]
            encrypted = header != b'SQLi'
            stats['dropped'][f'{name}_encrypted_db' if encrypted else f'{name}_db'] += 1
        elif base.exists():
            stats['dropped'][f'{name}_no_chat_db'] += 1
    stats['note'] = ('Trae/Trae CN chats live in an encrypted (SQLCipher) database; '
                     'the typed-input history has no timestamps or replies, so nothing is mined.')
    return []


# --------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=Path.home() / '.ytstack-prefs' / 'other',
                        help='Rows go to <out>/rows.jsonl; keep it outside the repository.')
    parser.add_argument('--skip-session', action='append', default=[],
                        help='Claude Code session id to leave out, such as the session coordinating this run. Repeatable.')
    args = parser.parse_args()
    SKIP_CLAUDE_SESSIONS.update(args.skip_session)
    args.out.mkdir(parents=True, exist_ok=True)
    home = Path.home()
    sources = [
        ('claude-code', mine_claude, home),
        ('pi', mine_pi, home),
        ('cursor-editor', mine_cursor_editor,
         home / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb'),
        ('cursor-cli', mine_cursor_cli, home),
        ('trae', check_trae, home),
    ]
    all_rows, summary = [], {}
    for name, miner, target in sources:
        stats = new_stats()
        rows = miner(target, stats) if target.exists() else []
        summary[name] = stats
        all_rows += rows
    all_rows.sort(key=lambda r: (r['date'], r['source'], r['session'], r['idx']))
    with (args.out / 'rows.jsonl').open('w') as handle:
        for row in all_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps({'out': str(args.out / 'rows.jsonl'), 'total': len(all_rows),
                      'sources': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
