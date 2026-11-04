#!/usr/bin/env python3
"""Run the frozen v07 prompts.

Control installs the current package without in-your-own-words, ketchup, and
teach. Treatment installs the whole package. Both get the same --voice rules.
Fixtures come from fixtures/build.py. This file does not git init, so T2 keeps
the history that builder wrote. v02's harness is imported only for parsing,
timeouts, and the per-model slots; nothing under evaluation/v02 is modified.

codex exec resume has no --sandbox flag. The follow-up passes
-c sandbox_mode="..." instead. Each exec and each resume counts, including
retries. The count is evaluation/v07/results/codex-call-count.json.
"""
import argparse
import concurrent.futures as cf
import fcntl
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'evaluation/v02'))
import harness

RUNNER_REV = 1
REFUSE_AT = 290
NEW_SKILLS = ('in-your-own-words', 'ketchup', 'teach')
RESULTS = HERE / 'results'
COUNTER_PATH = RESULTS / 'codex-call-count.json'
PROMPTS_PATH = HERE / 'prompts.json'
INSTALL = REPO / 'tools/install.py'
MODELS = (('gpt-6.1-sol', 2), ('gpt-6-astra', 1))
PILOT_CASES = ('K1', 'T2')
SKIP_PARTS = {'__pycache__', '.git'}

FIXTURES = None


def load_fixtures():
    global FIXTURES
    if FIXTURES is not None:
        return FIXTURES
    path = HERE / 'fixtures/build.py'
    spec = importlib.util.spec_from_file_location('v07_fixtures_build', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    FIXTURES = module
    return module


def skill_names():
    manifest = json.loads((REPO / 'ytstack.json').read_text())
    return manifest['primary_skills'] + manifest['support_skills']


def short_model(model):
    return model.rsplit('-', 1)[-1]


def global_note():
    home = Path.home()

    def names(root):
        if not root.is_dir():
            return []
        found = []
        for path in sorted(root.iterdir(), key=lambda item: item.name):
            if path.is_dir():
                found.append(path.name)
        return found

    agents = names(home / '.agents/skills')
    codex = names(home / '.codex/skills')
    system = home / '.codex/skills/.system'
    if system.is_dir():
        codex += ['.system/' + path.name for path in sorted(system.iterdir(), key=lambda item: item.name)]
    known = set(agents) | set(codex)
    present = [name for name in NEW_SKILLS if name in known]
    agents_md = home / '.codex/AGENTS.md'
    mentioned = []
    if agents_md.is_file():
        text = agents_md.read_text(errors='replace')
        mentioned = [name for name in NEW_SKILLS if name in text]
    return {
        'sentence': (
            '两组共用本机全局技能和 ~/.codex/AGENTS.md，评测没有改它们；'
            '全局发现路径里没有 in-your-own-words、ketchup、teach。'
        ),
        'agents_skills': agents,
        'codex_skills': codex,
        'new_skills_in_global_dirs': present,
        'codex_agents_md_exists': agents_md.is_file(),
        'codex_agents_md_mentions_new_skills': mentioned,
        'user_config_sandbox_mode': 'danger-full-access',
        'sandbox_override': (
            '新会话传 --sandbox，覆盖用户配置里的 danger-full-access。'
            'codex exec resume 没有 --sandbox，第二轮改传 -c sandbox_mode。'
        ),
    }


def reserve_call(job_id, phase, attempt, model):
    """Count one CLI call. Return False once the file already shows 290."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    with COUNTER_PATH.open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read()
        if raw.strip():
            try:
                data = json.loads(raw)
            except ValueError as exc:
                raise SystemExit(f'codex call counter is unreadable; refusing to call: {exc}') from exc
        else:
            data = {'count': 0, 'refuse_at': REFUSE_AT, 'calls': []}
        if data.get('count', 0) >= REFUSE_AT:
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False, data.get('count', 0)
        data['count'] += 1
        data['refuse_at'] = REFUSE_AT
        data['calls'].append({
            'n': data['count'], 'job': job_id, 'phase': phase,
            'attempt': attempt, 'model': model, 'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        })
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(data, ensure_ascii=False, indent=1))
        handle.flush()
        count = data['count']
        fcntl.flock(handle, fcntl.LOCK_UN)
        return True, count


def call_count():
    if not COUNTER_PATH.is_file():
        return 0
    return json.loads(COUNTER_PATH.read_text()).get('count', 0)


def parse_events(stdout):
    messages, commands, usage, thread = harness.parse(stdout or '')
    types = set()
    hints = []
    hint = ('read-only', 'sandbox', 'not permitted', 'operation not permitted', 'Read-only')
    for line in (stdout or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type'):
            types.add(event['type'])
        item = event.get('item') or {}
        if item.get('type'):
            types.add('item:' + str(item['type']))
        blob = json.dumps(item, ensure_ascii=False)
        if any(token in blob for token in hint):
            hints.append(blob[:360])
    return messages, commands, usage, thread, sorted(types), hints[:6]


def skills_in(commands):
    names = skill_names()
    found = set()
    for command in commands:
        for name in names:
            if f'skills/{name}/SKILL.md' in command:
                found.add(name)
    return sorted(found)


def codex_call(cwd, model, prompt, sandbox, job_id, phase, resume=None):
    cmd = ['codex', 'exec']
    if resume:
        # resume's help has no --sandbox. -c overrides config.toml for this process.
        cmd += ['resume', '--json', '--skip-git-repo-check', '-m', model,
                '-c', f'sandbox_mode="{sandbox}"', resume]
    else:
        cmd += ['--json', '--skip-git-repo-check', '-m', model, '--sandbox', sandbox]
    cmd.append(prompt)
    last = None
    for attempt in range(1, harness.ATTEMPTS[model] + 1):
        allowed, count = reserve_call(job_id, phase, attempt, model)
        if not allowed:
            return [], [], None, None, 'budget', 0.0, '', [], [], count
        start = time.time()
        with harness.SLOTS[model]:
            process = subprocess.Popen(
                cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                start_new_session=True)
            try:
                out, err = process.communicate(timeout=harness.TIMEOUT[model])
                code = process.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                out, err = process.communicate()
                code = 'timeout'
        messages, commands, usage, thread, types, hints = parse_events(out)
        seconds = round(time.time() - start, 1)
        last = (messages, commands, usage, thread, code, seconds, (err or '')[-2000:], types, hints, count)
        if code == 0 and usage:
            return last
        # A bad flag fails immediately. Don't spend the rest of the attempts on it.
        if isinstance(code, int) and code != 0 and seconds < 8 and err and 'sandbox_mode' in err:
            return last
    return last


def fingerprint(root):
    files = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if set(Path(relative).parts) & SKIP_PARTS or relative.endswith('.pyc'):
            continue
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = '\n'.join(f'{files[name]}  {name}' for name in sorted(files)).encode()
    return hashlib.sha256(payload).hexdigest(), files


def diff_maps(before_files, after_files):
    added = sorted(set(after_files) - set(before_files))
    removed = sorted(set(before_files) - set(after_files))
    changed = sorted(
        name for name in set(before_files) & set(after_files)
        if before_files[name] != after_files[name])
    return {'added': added, 'removed': removed, 'changed': changed}


def git_head(project):
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'], cwd=project, capture_output=True, text=True)
    return result.stdout.strip()


def git_count(project):
    result = subprocess.run(
        ['git', 'rev-list', '--count', 'HEAD'], cwd=project, capture_output=True, text=True)
    return result.stdout.strip()


def snapshot(project):
    digest, files = fingerprint(project)
    return {'digest': digest, 'files': files, 'head': git_head(project), 'commits': git_count(project)}


def compare(before, after):
    diff = diff_maps(before['files'], after['files'])
    diff['digest_before'] = before['digest']
    diff['digest_after'] = after['digest']
    diff['head_before'] = before['head']
    diff['head_after'] = after['head']
    diff['commits_before'] = before['commits']
    diff['commits_after'] = after['commits']
    diff['unchanged'] = (
        not diff['added'] and not diff['removed'] and not diff['changed']
        and before['head'] == after['head'])
    return diff


def text_of_changes(project, diff):
    texts = {}
    for relative in diff['added'] + diff['changed']:
        if not (relative.endswith('.md') or 'HANDOFF' in relative):
            continue
        path = project / relative
        if path.is_file():
            texts[relative] = path.read_text(errors='replace')[:100000]
    return texts


def installed_skills(project):
    root = project / '.agents/skills'
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if (path / 'SKILL.md').is_file())


def new_skill_paths(project):
    hits = []
    for path in project.rglob('*'):
        relative = path.relative_to(project).as_posix()
        padded = f'/{relative}/'
        for name in NEW_SKILLS:
            if f'/{name}/' in padded or relative == name or relative.endswith('/' + name):
                hits.append(relative)
                break
    return hits


def install_skills(project, arm):
    command = [sys.executable, str(INSTALL), '--project', str(project),
               '--harness', 'codex', '--method', 'copy', '--voice']
    if arm == 'control':
        manifest = json.loads((REPO / 'ytstack.json').read_text())
        for name in manifest['primary_skills']:
            if name not in NEW_SKILLS:
                command += ['--skill', name]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'install failed')
    names = installed_skills(project)
    hits = new_skill_paths(project)
    if arm == 'control' and (hits or any(name in names for name in NEW_SKILLS)):
        raise RuntimeError(f'control project can see new skills: {hits or names}')
    if arm == 'treatment' and any(name not in names for name in NEW_SKILLS):
        raise RuntimeError(f'treatment missing new skills, has {names}')
    return names


def prepare(parent, fixture, arm):
    module = load_fixtures()
    builder = getattr(module, f'build_{fixture.lower()}')
    try:
        builder(parent)
    except SystemExit as exc:
        raise RuntimeError(f'fixture {fixture} failed: {exc}') from exc
    project = parent / fixture
    if not project.is_dir():
        raise RuntimeError(f'fixture {fixture} did not create {project.name}')
    names = install_skills(project, arm)
    return project, names


def scrub(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [scrub(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item, replacements) for key, item in value.items()}
    return value


def replacements_for(project, parent):
    paths = []
    for path in (project, parent):
        paths.append(str(path))
        paths.append(str(path.resolve()))
    paths.append(str(Path.home()))
    home = str(Path.home())
    paths = sorted(set(paths), key=len, reverse=True)
    return [(path, '<home>' if path == home else '<project>') for path in paths]


def execute(job, note):
    record = {
        'id': job['id'], 'kind': job['kind'], 'case': job['case'], 'arm': job['arm'],
        'model': job['model'], 'rep': job['rep'], 'prompt': job['prompt'],
        'sandbox': job['sandbox'], 'runner_rev': RUNNER_REV,
        'global_note': note['sentence'],
        'resume_sandbox_note': (
            'codex exec resume 没有 --sandbox。第二轮传 -c sandbox_mode，'
            '值是这一题的 followup_sandbox；有没有真的拦住写文件，看 fingerprint。'
        ),
    }
    if job.get('followup'):
        record['followup'] = job['followup']
        record['followup_sandbox'] = job['followup_sandbox']
    if job['kind'] == 'trigger':
        record['expect_skill'] = job['expect_skill']
        record['should_trigger'] = job['should_trigger']
    with tempfile.TemporaryDirectory(prefix='ytev07-') as temp:
        parent = Path(temp)
        project, names = prepare(parent, job['fixture'], job['arm'])
        record['installed_skills'] = names
        record['control_new_skill_paths'] = new_skill_paths(project) if job['arm'] == 'control' else []
        before = snapshot(project)
        messages, commands, usage, thread, code, seconds, err, types, hints, _count = codex_call(
            project, job['model'], job['prompt'], job['sandbox'], job['id'], 'exec')
        after = snapshot(project)
        record.update({
            'exit': code, 'seconds': seconds, 'usage': usage,
            'final': messages[-1] if messages else '',
            'commentary': messages[:-1],
            'skills_read': skills_in(commands),
            'commands': [command[:400] for command in commands],
            'event_types': types,
            'sandbox_hints': hints,
            'stderr_tail': err,
            'thread_id': thread,
            'turn_files': compare(before, after),
        })
        if job.get('followup') and thread and code == 0:
            mid = snapshot(project)
            m2, c2, u2, _t2, code2, s2, err2, types2, hints2, _n2 = codex_call(
                project, job['model'], job['followup'], job['followup_sandbox'],
                job['id'], 'resume', resume=thread)
            end = snapshot(project)
            follow = compare(mid, end)
            record.update({
                'followup_final': m2[-1] if m2 else '',
                'followup_commentary': m2[:-1],
                'followup_skills': skills_in(c2),
                'followup_commands': [command[:400] for command in c2],
                'followup_exit': code2,
                'followup_seconds': s2,
                'followup_usage': u2,
                'followup_event_types': types2,
                'followup_sandbox_hints': hints2,
                'followup_stderr_tail': err2,
                'followup_files': follow,
                'followup_texts': text_of_changes(project, follow),
            })
        elif job.get('followup'):
            record['followup_exit'] = 'skipped'
            record['followup_files'] = None
        status = 'ok'
        if code == 'budget' or record.get('followup_exit') == 'budget':
            status = 'budget'
        elif code == 'timeout' or record.get('followup_exit') == 'timeout':
            status = 'timeout'
        elif code != 0 or not usage:
            status = 'failed'
        elif job.get('followup') and (record.get('followup_exit') != 0 or not record.get('followup_usage')):
            status = 'failed' if record.get('followup_exit') != 'timeout' else 'timeout'
        record['status'] = status
        if status == 'failed':
            record['error'] = err or record.get('followup_stderr_tail') or f'exit {code}'
        replacements = replacements_for(project, parent)
    return scrub(record, replacements)


def cached_ok(path):
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text())
    except ValueError:
        return False
    return data.get('status') == 'ok' and data.get('runner_rev') == RUNNER_REV


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n')
    temporary.replace(path)


def run_one(job, out_dir, note):
    target = out_dir / f"{job['id']}.json"
    if cached_ok(target):
        return job['id'], 'cached'
    print(f"start {job['id']}", flush=True)
    try:
        record = execute(job, note)
    except (Exception, SystemExit) as exc:
        record = {
            'id': job['id'], 'kind': job.get('kind'), 'case': job.get('case'),
            'arm': job.get('arm'), 'model': job.get('model'), 'rep': job.get('rep'),
            'status': 'failed', 'runner_rev': RUNNER_REV,
            'error': f'{type(exc).__name__}: {exc}',
            'global_note': note['sentence'],
        }
        record = scrub(record, [(str(Path.home()), '<home>')])
    write_json(target, record)
    print(f"done {job['id']} {record['status']}", flush=True)
    return job['id'], record['status']


def blind_jobs(prompts):
    jobs = []
    for case, spec in prompts.items():
        if not isinstance(spec, dict) or case.startswith('_') or case == 'triggers':
            continue
        for model, reps in MODELS:
            for rep in range(1, reps + 1):
                for arm in ('control', 'treatment'):
                    job = {
                        'id': f'{case}-{short_model(model)}-{arm}-r{rep}',
                        'kind': 'blind', 'case': case, 'fixture': spec['fixture'],
                        'arm': arm, 'model': model, 'rep': rep,
                        'prompt': spec['prompt'], 'sandbox': spec['sandbox'],
                    }
                    if spec.get('turns') == 2:
                        job['followup'] = spec['followup']
                        job['followup_sandbox'] = spec['followup_sandbox']
                    jobs.append(job)
    return jobs


def trigger_jobs(prompts):
    jobs = []
    for skill, spec in prompts['triggers'].items():
        if skill.startswith('_'):
            continue
        for label, key, should in (('y', '应该触发', True), ('n', '不该触发', False)):
            for index, phrase in enumerate(spec[key], 1):
                for model, _reps in MODELS:
                    jobs.append({
                        'id': f'trig-{skill}-{label}{index}-{short_model(model)}',
                        'kind': 'trigger', 'case': 'I1', 'fixture': 'I1',
                        'arm': 'treatment', 'model': model, 'rep': 1,
                        'prompt': phrase, 'sandbox': 'read-only',
                        'expect_skill': skill, 'should_trigger': should,
                    })
    return jobs


def run_jobs(jobs, note):
    pending = [job for job in jobs if not cached_ok(RESULTS / f"{job['id']}.json")]
    print(f'jobs {len(jobs)} pending {len(pending)} cached {len(jobs) - len(pending)}', flush=True)
    if not pending:
        return
    workers = min(8, len(pending))
    with cf.ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(run_one, job, RESULTS, note) for job in pending]
        for future in cf.as_completed(futures):
            job_id, status = future.result()
            print(f'result {job_id} {status} calls {call_count()}', flush=True)


def check_setup():
    note = global_note()
    print(note['sentence'])
    print('global new skills:', note['new_skills_in_global_dirs'] or 'none')
    load_fixtures()
    with tempfile.TemporaryDirectory(prefix='ytev07-check-') as temp:
        parent = Path(temp)
        checked = []
        for fixture, arm in (
            ('K1', 'control'), ('K1', 'treatment'), ('T2', 'control'), ('T2', 'treatment'),
            ('H1', 'control'), ('K2', 'treatment'), ('J1', 'control'),
        ):
            # Each prepare needs a fresh parent folder name. build_* writes parent/FIXTURE
            # and deletes that case first, so reuse is safe per fixture but arms overwrite.
            case_parent = parent / f'{fixture}-{arm}'
            case_parent.mkdir()
            project, names = prepare(case_parent, fixture, arm)
            commits = git_count(project)
            checked.append((fixture, arm, names, commits, new_skill_paths(project)))
            print(f'{fixture} {arm} skills={names} commits={commits} new_paths={new_skill_paths(project)}')
        control_voice = (parent / 'K1-control/K1/AGENTS.md').read_text()
        treatment_voice = (parent / 'K1-treatment/K1/AGENTS.md').read_text()
        if control_voice != treatment_voice:
            raise SystemExit('voice rules differ between arms')
        t2 = parent / 'T2-control/T2'
        log = subprocess.run(['git', 'log', '--format=%s'], cwd=t2, capture_output=True, text=True)
        print('T2 subjects:', ' | '.join(log.stdout.splitlines()))
        if git_count(t2) != '2':
            raise SystemExit('T2 history was overwritten')
    print('setup ok')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true', help='K1 and T2, both arms, Sol once')
    parser.add_argument('--check-setup', action='store_true', help='Build and install only; no codex call')
    parser.add_argument('--only', help='Comma-separated job ids')
    parser.add_argument('--triggers-only', action='store_true')
    parser.add_argument('--skip-triggers', action='store_true')
    args = parser.parse_args()
    if args.check_setup:
        check_setup()
        return
    prompts = json.loads(PROMPTS_PATH.read_text())
    note = global_note()
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS / 'environment.json', scrub(note, [(str(Path.home()), '<home>')]))
    jobs = [] if args.triggers_only else blind_jobs(prompts)
    triggers = [] if args.pilot or args.skip_triggers else trigger_jobs(prompts)
    if args.pilot:
        jobs = [job for job in jobs if job['case'] in PILOT_CASES and job['model'] == 'gpt-6.1-sol' and job['rep'] == 1]
    if args.only:
        wanted = {item.strip() for item in args.only.split(',') if item.strip()}
        jobs = [job for job in jobs if job['id'] in wanted]
        triggers = [job for job in triggers if job['id'] in wanted]
    print(f'blind {len(jobs)} trigger {len(triggers)} counter {call_count()}', flush=True)
    run_jobs(jobs, note)
    run_jobs(triggers, note)
    print(f'finished counter {call_count()}', flush=True)


if __name__ == '__main__':
    main()
