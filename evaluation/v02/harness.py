#!/usr/bin/env python3
"""Run frozen prompts through real Codex CLI sessions; keep replies, skill reads, and usage only."""
import argparse, concurrent.futures as cf, json, os, shutil, signal, subprocess, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIX = REPO / 'evaluation/ab-create-test-20261102/fixture'
PACKAGES = {'v01': REPO / 'evaluation/snapshots/v01', 'v02': REPO / 'evaluation/snapshots/v02'}
TARGET_TOOLS = REPO / 'evaluation/snapshots/v01'
SLOTS = {'gpt-6-astra': threading.BoundedSemaphore(2), 'gpt-6.1-sol': threading.BoundedSemaphore(6)}
ATTEMPTS = {'gpt-6-astra': 3, 'gpt-6.1-sol': 2}
TIMEOUT = {'gpt-6-astra': 900, 'gpt-6.1-sol': 420}


def workbench(path, package, agents_md):
    path.mkdir(parents=True)
    shutil.copy2(REPO / 'tests/fixtures/tiny-queue/queue_cli.py', path)
    for name in ['expense_cli.py', 'README.md']:
        shutil.copy2(FIX / name, path)
    shutil.copytree(FIX / 'tests', path / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
    # Both arms read the same frozen copy, so package changes never alter the question's subject.
    shutil.copytree(TARGET_TOOLS / 'tools', path / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(TARGET_TOOLS / 'ytstack.json', path)
    shutil.copy2(REPO / 'tests/test_package.py', path / 'tests/test_package.py')
    subprocess.run(['git', 'init', '-q', '.'], cwd=path, check=True)
    subprocess.run(['python3', str(PACKAGES[package] / 'tools/install.py'), '--project', str(path),
                    '--harness', 'codex', '--method', 'copy'], check=True, capture_output=True)
    if agents_md:
        shutil.copy2(agents_md, path / 'AGENTS.md')


def parse(stdout):
    messages, commands, usage, thread = [], [], None, None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'thread.started':
            thread = event.get('thread_id')
        if event.get('type') == 'turn.completed':
            usage = event.get('usage')
        item = event.get('item') or {}
        if event.get('type') == 'item.completed':
            if item.get('type') == 'agent_message':
                messages.append(item.get('text', ''))
            elif item.get('type') == 'command_execution':
                commands.append(item.get('command', ''))
    return messages, commands, usage, thread


def codex(cwd, model, prompt, sandbox, resume=None):
    base = ['codex', 'exec']
    if resume:
        base += ['resume', resume]
    cmd = base + ['--json', '--skip-git-repo-check', '-m', model]
    if not resume:
        cmd += ['--sandbox', sandbox]
    cmd.append(prompt)
    result = None
    for _ in range(ATTEMPTS[model]):
        start = time.time()
        with SLOTS[model]:
            # New session so a timeout also kills the native child, which outlives its node wrapper.
            p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True, start_new_session=True)
            try:
                out, _err = p.communicate(timeout=TIMEOUT[model])
                code = p.returncode
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                out, _err = p.communicate()
                code = 'timeout'
        result = (*parse(out), code, round(time.time() - start, 1))
        if code == 0 and result[2]:
            return result
    return result


def run_one(job, out_dir):
    target = out_dir / f"{job['id']}.json"
    if target.exists():
        return job['id'], 'cached'
    with tempfile.TemporaryDirectory(prefix='ytev-') as temp:
        project = Path(temp) / 'project'
        workbench(project, job['package'], job.get('agents_md'))
        messages, commands, usage, thread, code, seconds = codex(
            project, job['model'], job['prompt'], job.get('sandbox', 'read-only'))
        record = {**job, 'status': 'ok' if code == 0 and usage else 'failed', 'exit': code, 'seconds': seconds, 'usage': usage,
                  'final': messages[-1] if messages else '', 'commentary': messages[:-1],
                  'skills_read': sorted({s for c in commands for s in
                                         ['acceptance-criteria', 'create-test-skill', 'bro', 'technical-bro', 'unslop']
                                         if f'skills/{s}/SKILL.md' in c}),
                  'commands': [c[:220] for c in commands]}
        if job.get('followup') and thread:
            m2, c2, u2, _, code2, s2 = codex(project, job['model'], job['followup'], 'read-only', resume=thread)
            record['followup_final'] = m2[-1] if m2 else ''
            record['followup_skills'] = sorted({s for c in c2 for s in ['bro', 'unslop'] if f'skills/{s}/SKILL.md' in c})
            record['followup_exit'] = code2
    if record['status'] == 'ok':
        target.write_text(json.dumps(record, ensure_ascii=False, indent=1))
    else:
        target.with_suffix('.failed').write_text(json.dumps(record, ensure_ascii=False, indent=1))
    return job['id'], record['status']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('jobs', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=10)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(a.jobs.read_text())
    with cf.ThreadPoolExecutor(a.workers) as pool:
        for fut in cf.as_completed([pool.submit(run_one, j, a.out) for j in jobs]):
            print(*fut.result(), flush=True)


if __name__ == '__main__':
    main()
