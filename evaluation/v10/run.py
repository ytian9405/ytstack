#!/usr/bin/env python3
"""Run the frozen v10 prompts.

Both arms install the current package with --method copy --voice. Control then
replaces unslop with the copy from commit a5bfa83 (the version before the two
rewritten Chinese rules). Treatment keeps the file from this checkout.

Every case is single-turn and read-only: Codex gets one prompt that asks it to
rewrite one frozen draft under docs/ and put the full rewritten text in its
reply. Planned calls are 6 cases x (2 Sol + 1 Astra) x 2 arms = 36; retries are
counted too and the runner refuses at REFUSE_AT.

The codex subprocess gets its own HOME and CODEX_HOME. HOME is empty, so the
global ~/.agents/skills links are not visible. CODEX_HOME has a copied auth
file and a minimal config, and no skills directory. This process does not
read the auth file and does not modify ~/.agents or ~/.codex.

Self-check: python3 run.py --check builds every fixture, installs both arms,
loads the prompts, and reports which installed files differ between the arms.
At freeze time the worktree unslop still equals a5bfa83, so the report says
the arms are identical; after the rule rewrite the only difference must be
.agents/skills/unslop/SKILL.md. No codex call happens under --check.
"""
import argparse
import atexit
import concurrent.futures as cf
import fcntl
import getpass
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
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
REFUSE_AT = 150
CONTROL_REV = 'a5bfa83'
VARIED = ('unslop',)
RESULTS = HERE / 'results'
COUNTER_PATH = RESULTS / 'codex-call-count.json'
PROMPTS_PATH = HERE / 'prompts.json'
INSTALL = REPO / 'tools/install.py'
MODELS = (('gpt-6.1-sol', 2), ('gpt-6-astra', 1))
PILOT_CASES = ('W1',)
SKIP_PARTS = {'__pycache__', '.git'}
HINT_WORDS = ('说人话', '大白话', '通俗', '别用术语', '小白', '术语少', '易懂')
SKILL_WORD = re.compile(r'\$(unslop|technical-bro)\b')

MINIMAL_CONFIG = """model = "gpt-6.1-sol"
model_reasoning_effort = "high"
personality = "pragmatic"
approval_policy = "never"
sandbox_mode = "read-only"

[shell_environment_policy]
exclude = ["CODEX_HOME"]
"""

JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')
SK_RE = re.compile(r'\bsk-[A-Za-z0-9]{12,}\b')
TOKEN_ASSIGN_RE = re.compile(
    r'(?i)("?(?:access_token|refresh_token|id_token|api_key)"?\s*[:=]\s*"?)[^"\s,}]+')

CLEANUP = []
FIXTURES = None


def remember(path):
    CLEANUP.append(path)
    return path


def cleanup_temps():
    for path in CLEANUP:
        shutil.rmtree(path, ignore_errors=True)


atexit.register(cleanup_temps)


def load_fixtures():
    global FIXTURES
    if FIXTURES is not None:
        return FIXTURES
    path = HERE / 'fixtures/build.py'
    spec = importlib.util.spec_from_file_location('v10_fixtures_build', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    FIXTURES = module
    return module


def skill_names():
    manifest = json.loads((REPO / 'ytstack.json').read_text())
    return manifest['primary_skills'] + manifest['support_skills']


def short_model(model):
    return model.rsplit('-', 1)[-1]


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def git_show_bytes(rev, relative):
    return subprocess.check_output(['git', 'show', f'{rev}:{relative}'], cwd=REPO)


def expected_hashes():
    found = {'control': {}, 'treatment': {}}
    for name in VARIED:
        found['treatment'][name] = sha256_bytes((REPO / 'skills' / name / 'SKILL.md').read_bytes())
        found['control'][name] = sha256_bytes(git_show_bytes(CONTROL_REV, f'skills/{name}/SKILL.md'))
    others = {}
    for name in skill_names():
        if name in VARIED:
            continue
        others[name] = sha256_bytes((REPO / 'skills' / name / 'SKILL.md').read_bytes())
    return found, others


def control_tree():
    if control_tree.cached is not None:
        return control_tree.cached
    dest = remember(Path(tempfile.mkdtemp(prefix='ytstack-v10-skills-')))
    blob = subprocess.check_output(
        ['git', 'archive', CONTROL_REV, *[f'skills/{name}' for name in VARIED]], cwd=REPO)
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:') as archive:
        if hasattr(tarfile, 'data_filter'):
            archive.extractall(dest, filter='data')
        else:
            archive.extractall(dest)
    for name in VARIED:
        if not (dest / 'skills' / name / 'SKILL.md').is_file():
            raise SystemExit(f'missing {name} in {CONTROL_REV}')
    control_tree.cached = dest
    return dest


control_tree.cached = None


def codex_template():
    if codex_template.cached is not None:
        return codex_template.cached
    source = Path.home() / '.codex' / 'auth.json'
    if not source.is_file():
        raise SystemExit('codex auth file is missing; refusing to call codex')
    dest = remember(Path(tempfile.mkdtemp(prefix='ytstack-v10-codex-template-')))
    os.chmod(dest, 0o700)
    shutil.copy2(source, dest / 'auth.json')
    os.chmod(dest / 'auth.json', 0o600)
    (dest / 'config.toml').write_text(MINIMAL_CONFIG)
    names = sorted(path.name for path in dest.iterdir())
    if names != ['auth.json', 'config.toml']:
        raise SystemExit(f'isolated codex template has unexpected files: {names}')
    codex_template.cached = dest
    return dest


codex_template.cached = None


def make_codex_homes():
    """Return (empty HOME, CODEX_HOME) for one codex subprocess."""
    template = codex_template()
    empty = Path(tempfile.mkdtemp(prefix='ytstack-v10-empty-home-'))
    codex_dir = Path(tempfile.mkdtemp(prefix='ytstack-v10-codex-'))
    os.chmod(empty, 0o700)
    os.chmod(codex_dir, 0o700)
    shutil.copy2(template / 'auth.json', codex_dir / 'auth.json')
    shutil.copy2(template / 'config.toml', codex_dir / 'config.toml')
    os.chmod(codex_dir / 'auth.json', 0o600)
    if (empty / '.agents').exists() or (codex_dir / 'skills').exists():
        raise RuntimeError('isolated home can see a skills directory')
    return empty, codex_dir


def remove_tree(path):
    if path is not None:
        shutil.rmtree(path, ignore_errors=True)


def codex_child_env(empty, codex_dir):
    env = os.environ.copy()
    env['HOME'] = str(empty)
    env['CODEX_HOME'] = str(codex_dir)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    for key in list(env):
        if key.startswith('ORCA_'):
            env.pop(key, None)
            continue
        upper = key.upper()
        if any(word in upper for word in ('TOKEN', 'SECRET', 'PASSWORD', 'API_KEY', 'ACCESS_KEY')):
            env.pop(key, None)
    return env


def global_link_facts():
    facts = {}
    for name in VARIED:
        link = Path.home() / '.agents' / 'skills' / name
        worktree = (REPO / 'skills' / name / 'SKILL.md').resolve()
        facts[name] = {
            'symlink': link.is_symlink(),
            'points_at_worktree': link.is_symlink() and (link / 'SKILL.md').resolve() == worktree,
        }
    return {
        'method': (
            '每个 codex 子进程使用单独的空 HOME 和单独的 CODEX_HOME。'
            'HOME 下没有 .agents。CODEX_HOME 只有复制过来的 auth 文件和一份最小配置，没有 skills 目录。'
            'shell_environment_policy.exclude 含 CODEX_HOME，子进程的 shell 看不到这份目录。'
            '没有读取 auth 文件的内容，也没有改 ~/.agents 或 ~/.codex。'
        ),
        'global_links_point_at_worktree': facts,
        'hides_those_links': all(item['points_at_worktree'] for item in facts.values()),
    }


def isolation_note():
    facts = global_link_facts()
    return {
        'sentence': facts['method'],
        'global_links_point_at_worktree': facts['global_links_point_at_worktree'],
        'user_config_not_used': (
            '没有加载本机 ~/.codex/config.toml。子进程配置只写了模型、high reasoning、'
            'pragmatic、approval_policy=never、sandbox_mode=read-only，以及排除 CODEX_HOME。'
            '每题另传 --sandbox read-only。'
        ),
    }


def reserve_call(job_id, phase, attempt, model):
    """Count one CLI call. Return False once the file already shows REFUSE_AT."""
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
            data = {'count': 0, 'refuse_at': REFUSE_AT, 'limit': 200, 'calls': []}
        if data.get('count', 0) >= REFUSE_AT:
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False, data.get('count', 0)
        data['count'] += 1
        data['refuse_at'] = REFUSE_AT
        data['limit'] = 200
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


def reads_global_varied(command):
    markers = [
        str(Path.home() / '.agents' / 'skills' / name) for name in VARIED
    ]
    return any(marker in command for marker in markers)


def codex_call(cwd, model, prompt, sandbox, job_id, phase, child_env):
    cmd = ['codex', 'exec', '--json', '--skip-git-repo-check', '-m', model,
           '--sandbox', sandbox,
           '-c', 'approval_policy="never"',
           '-c', 'model_reasoning_effort="high"',
           prompt]
    last = None
    for attempt in range(1, harness.ATTEMPTS[model] + 1):
        with harness.SLOTS[model]:
            allowed, count = reserve_call(job_id, phase, attempt, model)
            if not allowed:
                return [], [], None, None, 'budget', 0.0, '', [], [], count, False
            start = time.time()
            process = subprocess.Popen(
                cmd, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding='utf-8', errors='replace', start_new_session=True)
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
        global_hit = any(reads_global_varied(command) for command in commands)
        last = (messages, commands, usage, thread, code, seconds, (err or '')[-2000:],
                types, hints, count, global_hit)
        if code == 0 and usage:
            return last
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


def git_text(project, args):
    result = subprocess.run(
        ['git', '-c', 'core.autocrlf=false', *args], cwd=project,
        capture_output=True, text=True)
    return result.returncode, result.stdout


def git_head(project):
    code, out = git_text(project, ['rev-parse', 'HEAD'])
    return out.strip() if code == 0 else ''


def git_count(project):
    code, out = git_text(project, ['rev-list', '--count', 'HEAD'])
    return out.strip() if code == 0 else ''


def git_facts(project):
    code, status = git_text(project, ['status', '--porcelain'])
    return {
        'status': (status if code == 0 else '')[:4000],
        'commits': git_count(project),
        'head': git_head(project),
    }


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


def installed_skills(project):
    root = project / '.agents/skills'
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if (path / 'SKILL.md').is_file())


def skill_sha256(project):
    found = {}
    root = project / '.agents' / 'skills'
    for path in sorted(root.glob('*/SKILL.md')):
        found[path.parent.name] = sha256_bytes(path.read_bytes())
    return found


def replace_with_control(project):
    source_root = control_tree() / 'skills'
    for name in VARIED:
        target = project / '.agents' / 'skills' / name
        if target.is_symlink():
            raise RuntimeError(f'refusing to replace a symlinked skill: {name}')
        resolved = target.resolve()
        if resolved == REPO or REPO in resolved.parents:
            raise RuntimeError(f'refusing to delete a skill inside the checkout: {name}')
        shutil.rmtree(target)
        shutil.copytree(source_root / name, target)


def install_skills(project, arm):
    command = [sys.executable, str(INSTALL), '--project', str(project),
               '--harness', 'codex', '--method', 'copy', '--voice']
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or 'install failed').strip()
        raise RuntimeError(detail)
    if arm == 'control':
        replace_with_control(project)
    names = installed_skills(project)
    missing = [name for name in VARIED if name not in names]
    if missing:
        raise RuntimeError(f'{arm} missing {missing}')
    hashes = skill_sha256(project)
    varied, others = expected_hashes()
    wanted = varied[arm]
    for name, digest in wanted.items():
        if hashes.get(name) != digest:
            raise RuntimeError(f'{arm} {name} hash is not the expected blob')
    for name, digest in others.items():
        if hashes.get(name) != digest:
            raise RuntimeError(f'{arm} shared skill {name} hash drifted')
    for name in VARIED:
        path = project / '.agents' / 'skills' / name
        if path.is_symlink():
            raise RuntimeError(f'{arm} {name} is still a symlink')
    return names, hashes


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
    names, hashes = install_skills(project, arm)
    return project, names, hashes


def redact_text(value):
    value = JWT_RE.sub('<redacted>', value)
    value = SK_RE.sub('<redacted>', value)
    value = TOKEN_ASSIGN_RE.sub(r'\1<redacted>', value)
    return value


def scrub(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            if old:
                value = value.replace(old, new)
        return redact_text(value)
    if isinstance(value, list):
        return [scrub(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item, replacements) for key, item in value.items()}
    return value


def base_replacements(*paths):
    username = getpass.getuser()
    items = [str(Path.home())]
    items.extend(str(path) for path in paths if path is not None)
    items.extend(str(path.resolve()) for path in paths if path is not None)
    unique = sorted({item for item in items if item}, key=len, reverse=True)
    pairs = [(item, '<home>' if item == str(Path.home()) else '<path>') for item in unique]
    pairs.append((username, '<user>'))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def assert_no_secrets(text):
    username = getpass.getuser()
    if username and username in text:
        raise RuntimeError('refusing to write a result that still contains the username')
    home = str(Path.home())
    if home and home in text:
        raise RuntimeError('refusing to write a result that still contains the home path')
    if 'eyJ' in text and JWT_RE.search(text):
        raise RuntimeError('refusing to write a result that still contains a token')


def skill_commands(commands):
    hits = []
    for command in commands:
        if any(f'skills/{name}/SKILL.md' in command for name in VARIED):
            hits.append(command[:400])
    return hits


def execute(job, note):
    varied, _others = expected_hashes()
    record = {
        'id': job['id'], 'kind': job['kind'], 'case': job['case'], 'arm': job['arm'],
        'model': job['model'], 'rep': job['rep'], 'prompt': job['prompt'],
        'doc': job['doc'], 'sandbox': job['sandbox'], 'runner_rev': RUNNER_REV,
        'global_note': note['sentence'],
        'isolation': note['user_config_not_used'],
        'read_only_note': (
            '这一题单轮、read-only。prompt 只要求把改好的全文写在回复里。'
            'turn_files 应当显示项目文件一个没动。'
        ),
        'expected_skill_sha256': varied[job['arm']],
    }
    empty = codex_dir = None
    try:
        empty, codex_dir = make_codex_homes()
        child_env = codex_child_env(empty, codex_dir)
        with tempfile.TemporaryDirectory(prefix='ytev10-') as temp:
            parent = Path(temp)
            project, names, hashes = prepare(parent, job['fixture'], job['arm'])
            record['installed_skills'] = names
            record['skill_sha256'] = {name: hashes[name] for name in VARIED}
            record['skill_sha256_match'] = record['skill_sha256'] == varied[job['arm']]
            record['shared_skill_sha256'] = {
                name: hashes[name] for name in hashes if name not in VARIED
            }
            before = snapshot(project)
            messages, commands, usage, thread, code, seconds, err, types, hints, _count, global_hit = codex_call(
                project, job['model'], job['prompt'], job['sandbox'], job['id'], 'exec', child_env)
            after = snapshot(project)
            record.update({
                'exit': code, 'seconds': seconds, 'usage': usage,
                'final': messages[-1] if messages else '',
                'commentary': messages[:-1],
                'skills_read': skills_in(commands),
                'skill_read_commands': skill_commands(commands),
                'read_global_varied': global_hit,
                'commands': [command[:400] for command in commands],
                'event_types': types,
                'sandbox_hints': hints,
                'stderr_tail': err,
                'thread_id': thread,
                'turn_files': compare(before, after),
                'git_after_turn': git_facts(project),
            })
            status = 'ok'
            if code == 'budget':
                status = 'budget'
            elif code == 'timeout':
                status = 'timeout'
            elif code != 0 or not usage:
                status = 'failed'
            record['status'] = status
            if status == 'failed':
                record['error'] = err or f'exit {code}'
            replacements = base_replacements(project, parent, empty, codex_dir)
        cleaned = scrub(record, replacements)
        assert_no_secrets(json.dumps(cleaned, ensure_ascii=False))
        return cleaned
    finally:
        remove_tree(empty)
        remove_tree(codex_dir)


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
    text = json.dumps(value, ensure_ascii=False, indent=1) + '\n'
    assert_no_secrets(text)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text)
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
        record = scrub(record, base_replacements())
        try:
            assert_no_secrets(json.dumps(record, ensure_ascii=False))
        except RuntimeError:
            record = {
                'id': job['id'], 'status': 'failed', 'runner_rev': RUNNER_REV,
                'error': 'withheld because the failure text still contained a local path or token',
            }
    write_json(target, record)
    print(f"done {job['id']} {record.get('status')} calls {call_count()}", flush=True)
    return job['id'], record.get('status')


def blind_jobs(prompts):
    jobs = []
    for case, spec in prompts.items():
        if not isinstance(spec, dict) or case.startswith('_'):
            continue
        if spec.get('turns') != 1:
            raise SystemExit(f'{case} must be single-turn; this runner has no resume path')
        for model, reps in MODELS:
            for rep in range(1, reps + 1):
                for arm in ('control', 'treatment'):
                    jobs.append({
                        'id': f'{case}-{short_model(model)}-{arm}-r{rep}',
                        'kind': 'blind', 'case': case, 'fixture': spec['fixture'],
                        'arm': arm, 'model': model, 'rep': rep,
                        'doc': spec['doc'],
                        'prompt': spec['prompt'], 'sandbox': spec['sandbox'],
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


def write_skill_hashes(sample):
    varied, others = expected_hashes()
    payload = {
        'control_revision': CONTROL_REV,
        'treatment': 'worktree',
        'skill_md_sha256': varied,
        'varied_differ': all(varied['control'][name] != varied['treatment'][name] for name in VARIED),
        'shared_skill_md_sha256': others,
        'installed_sample': sample,
    }
    write_json(RESULTS / 'skill-hashes.json', payload)


def write_version_proof():
    proof = None
    for path in sorted(RESULTS.glob('*-control-*.json')):
        try:
            record = json.loads(path.read_text())
        except ValueError:
            continue
        if record.get('status') != 'ok' or record.get('arm') != 'control':
            continue
        read = set(record.get('skills_read') or [])
        varied_read = sorted(read & set(VARIED))
        if not varied_read:
            continue
        commands = record.get('skill_read_commands') or []
        if record.get('read_global_varied'):
            continue
        expected = record.get('expected_skill_sha256') or {}
        actual = record.get('skill_sha256') or {}
        if not expected or actual != expected:
            continue
        proof = {
            'run_id': record.get('id'),
            'skills_read': record.get('skills_read') or [],
            'varied_skills_read': varied_read,
            'skill_read_commands': commands,
            'read_global_varied': False,
            'skill_sha256': actual,
            f'matches_{CONTROL_REV}': True,
            'sentence': (
                f"{record.get('id')} 的 skills_read 读了项目里的 "
                f"{'、'.join(varied_read)}，命令路径不是全局 ~/.agents/skills，"
                f'unslop 的 SKILL.md sha256 等于提交 {CONTROL_REV}。'
            ),
        }
        break
    if proof is None:
        proof = {
            f'matches_{CONTROL_REV}': False,
            'sentence': f'还没有一次成功的对照组运行读到 unslop 的项目副本（应等于提交 {CONTROL_REV}）。',
        }
    write_json(RESULTS / 'version-proof.json', proof)
    print(proof['sentence'])


def check_prompts(prompts):
    cases = [key for key in prompts if not key.startswith('_')]
    if sorted(cases) != ['C1', 'M1', 'R1', 'R2', 'W1', 'W2']:
        raise SystemExit(f'expected six frozen cases W1/W2/R1/R2/C1/M1, got {sorted(cases)}')
    planned = 0
    for case in cases:
        spec = prompts[case]
        for field in ('fixture', 'sandbox', 'doc', 'prompt'):
            if not spec.get(field):
                raise SystemExit(f'{case} is missing {field}')
        if spec['fixture'] != case or spec['sandbox'] != 'read-only':
            raise SystemExit(f'{case} fixture/sandbox drifted: {spec["fixture"]}/{spec["sandbox"]}')
        if not SKILL_WORD.search(spec['prompt']):
            raise SystemExit(f'{case} prompt does not name $unslop or $technical-bro')
        if spec['doc'] not in spec['prompt']:
            raise SystemExit(f'{case} prompt does not point at its draft file {spec["doc"]}')
        for word in HINT_WORDS:
            if word in spec['prompt']:
                raise SystemExit(f'{case} prompt contains the hint word {word!r}')
        for model, reps in MODELS:
            planned += reps
    planned *= 2
    print(f'prompts ok: 6 cases, single-turn, planned calls {planned} (refuse at {REFUSE_AT})')
    return planned


def arm_diff_files(left, right):
    _, left_files = fingerprint(left)
    _, right_files = fingerprint(right)
    diff = diff_maps(left_files, right_files)
    names = sorted(set(diff['added']) | set(diff['removed']) | set(diff['changed']))
    return names


def check_setup():
    note = isolation_note()
    print(note['sentence'])
    prompts = json.loads(PROMPTS_PATH.read_text())
    planned = check_prompts(prompts)
    varied, others = expected_hashes()
    same_now = varied['control']['unslop'] == varied['treatment']['unslop']
    print(f"unslop sha256 control({CONTROL_REV})={varied['control']['unslop'][:12]}… "
          f"treatment(worktree)={varied['treatment']['unslop'][:12]}… "
          f"identical={same_now}")
    load_fixtures()
    codex_template()
    sample = {}
    with tempfile.TemporaryDirectory(prefix='ytev10-check-') as temp:
        parent = Path(temp)
        for case in ('W1', 'W2', 'R1', 'R2', 'C1', 'M1'):
            trees = {}
            for arm in ('control', 'treatment'):
                case_parent = parent / f'{case}-{arm}'
                case_parent.mkdir()
                project, names, hashes = prepare(case_parent, case, arm)
                sample.setdefault(arm, hashes)
                doc = project / prompts[case]['doc']
                if not doc.is_file():
                    raise SystemExit(f'{case} {arm} is missing the draft {prompts[case]["doc"]}')
                trees[arm] = project
                print(f'{case} {arm} skills={len(names)} commits={git_count(project)}')
            differ = arm_diff_files(trees['control'], trees['treatment'])
            allowed = {'.agents/skills/unslop/SKILL.md'}
            if not set(differ) <= allowed:
                raise SystemExit(f'{case}: arms differ beyond unslop: {differ}')
            if differ:
                print(f'{case}: arms differ only in {differ}')
            else:
                print(f'{case}: arms are identical '
                      '(worktree unslop still equals the control revision; expected at freeze time)')
        voice_a = (parent / 'W1-control/W1/AGENTS.md').read_text()
        voice_b = (parent / 'W1-treatment/W1/AGENTS.md').read_text()
        if voice_a != voice_b:
            raise SystemExit('voice rules differ between arms')
        for name, digest in others.items():
            if sample['control'][name] != digest or sample['treatment'][name] != digest:
                raise SystemExit(f'shared skill {name} is not the current blob in both arms')
            if sample['control'][name] != sample['treatment'][name]:
                raise SystemExit(f'shared skill {name} differs between arms')
        if same_now:
            print('self-check: the two arms install byte-identical trees. '
                  f'The worktree skills/unslop/SKILL.md still equals {CONTROL_REV}, which is the '
                  'state at freeze time. After the two rewritten rules land, rerun --check: it '
                  'must report that the arms differ only in .agents/skills/unslop/SKILL.md.')
        else:
            print('self-check: the arms differ only in .agents/skills/unslop/SKILL.md, as required.')
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_skill_hashes(sample)
    write_json(RESULTS / 'environment.json', scrub({
        **note,
        'skill_md_sha256': varied,
        'shared_skill_md_sha256': others,
        'varied_differ': not same_now,
        'shared_match': True,
        'planned_calls': planned,
        'refuse_at': REFUSE_AT,
    }, base_replacements()))
    print('setup ok')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true', help='W1, both arms, Sol once')
    parser.add_argument('--check', action='store_true',
                        help='Load prompts, build fixtures, install both arms, diff them; no codex call')
    parser.add_argument('--only', help='Comma-separated job ids')
    args = parser.parse_args()
    if args.check:
        check_setup()
        return
    prompts = json.loads(PROMPTS_PATH.read_text())
    note = isolation_note()
    varied, others = expected_hashes()
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS / 'environment.json', scrub({
        **note,
        'skill_md_sha256': varied,
        'shared_skill_md_sha256': others,
        'varied_differ': all(varied['control'][name] != varied['treatment'][name] for name in VARIED),
    }, base_replacements()))
    jobs = blind_jobs(prompts)
    if args.pilot:
        jobs = [
            job for job in jobs
            if job['case'] in PILOT_CASES and job['model'] == 'gpt-6.1-sol' and job['rep'] == 1
        ]
    if args.only:
        wanted = {item.strip() for item in args.only.split(',') if item.strip()}
        jobs = [job for job in jobs if job['id'] in wanted]
    print(f'blind {len(jobs)} counter {call_count()}', flush=True)
    run_jobs(jobs, note)
    write_version_proof()
    print(f'finished counter {call_count()}', flush=True)


if __name__ == '__main__':
    main()
