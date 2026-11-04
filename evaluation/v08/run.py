#!/usr/bin/env python3
"""Run the frozen v08 prompts.

Both arms install the current package with --method copy --voice. Control then
replaces ketchup, teach, and in-your-own-words with the copies from commit
7fb9483. Treatment keeps the files from this checkout.

The codex subprocess gets its own HOME and CODEX_HOME. HOME is empty, so the
global ~/.agents/skills links are not visible. CODEX_HOME has a copied auth
file and a minimal config, and no skills directory. This process does not
read the auth file and does not modify ~/.agents or ~/.codex.

codex exec resume has no --sandbox flag. The follow-up passes
-c sandbox_mode="..." instead. Each exec and each resume counts, including
retries. The count is evaluation/v08/results/codex-call-count.json.
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
REFUSE_AT = 145
CONTROL_REV = '7fb9483'
VARIED = ('ketchup', 'teach', 'in-your-own-words')
RESULTS = HERE / 'results'
COUNTER_PATH = RESULTS / 'codex-call-count.json'
PROMPTS_PATH = HERE / 'prompts.json'
INSTALL = REPO / 'tools/install.py'
MODELS = (('gpt-6.1-sol', 2), ('gpt-6-astra', 1))
PILOT_CASES = ('H1', 'T1')
SKIP_PARTS = {'__pycache__', '.git'}
SKIP_FILES = {'jobs/rollup-progress.json', 'jobs/rollup.pid'}
RUNTIME_NOTE = 'jobs/rollup-progress.json 和 jobs/rollup.pid 是评测自己启动的后台任务写的，不计入文件指纹。'

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
    spec = importlib.util.spec_from_file_location('v08_fixtures_build', path)
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
    dest = remember(Path(tempfile.mkdtemp(prefix='ytstack-v08-skills-')))
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
    dest = remember(Path(tempfile.mkdtemp(prefix='ytstack-v08-codex-template-')))
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
    empty = Path(tempfile.mkdtemp(prefix='ytstack-v08-empty-home-'))
    codex_dir = Path(tempfile.mkdtemp(prefix='ytstack-v08-codex-'))
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
            'HOME 下没有 .agents。CODEX_HOME 只有复制过来的登录文件和一份最小配置，没有 skills 目录。'
            'shell_environment_policy.exclude 含 CODEX_HOME，子进程的 shell 看不到这份目录。'
            '没有读取登录文件的内容，也没有改 ~/.agents 或 ~/.codex。'
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
            '每次调用仍另传 --sandbox 或 -c sandbox_mode。'
        ),
    }


def reserve_call(job_id, phase, attempt, model):
    """Count one CLI call. Return False once the file already shows 145."""
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
            data = {'count': 0, 'refuse_at': REFUSE_AT, 'limit': 150, 'calls': []}
        if data.get('count', 0) >= REFUSE_AT:
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False, data.get('count', 0)
        data['count'] += 1
        data['refuse_at'] = REFUSE_AT
        data['limit'] = 150
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


def reads_global_three(command):
    markers = [
        str(Path.home() / '.agents' / 'skills' / name) for name in VARIED
    ]
    return any(marker in command for marker in markers)


def codex_call(cwd, model, prompt, sandbox, job_id, phase, child_env, resume=None):
    cmd = ['codex', 'exec']
    if resume:
        cmd += ['resume', '--json', '--skip-git-repo-check', '-m', model,
                '-c', f'sandbox_mode="{sandbox}"',
                '-c', 'approval_policy="never"',
                '-c', 'model_reasoning_effort="high"',
                resume]
    else:
        cmd += ['--json', '--skip-git-repo-check', '-m', model, '--sandbox', sandbox,
                '-c', 'approval_policy="never"',
                '-c', 'model_reasoning_effort="high"']
    cmd.append(prompt)
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
        global_hit = any(reads_global_three(command) for command in commands)
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
        if relative in SKIP_FILES or set(Path(relative).parts) & SKIP_PARTS or relative.endswith('.pyc'):
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
    _, tracked = git_text(project, ['ls-files', '--', 'data/带走/三月账.json'])
    ignored = subprocess.run(
        ['git', 'check-ignore', '-q', '--', 'data/带走/三月账.json'], cwd=project)
    queue = project / 'queue_cli.py'
    work = queue.read_text(errors='replace') if queue.is_file() else ''
    _, head_queue = git_text(project, ['show', 'HEAD:queue_cli.py'])
    return {
        'status': (status if code == 0 else '')[:4000],
        'commits': git_count(project),
        'head': git_head(project),
        'march_tracked': bool(tracked.strip()),
        'march_ignored': ignored.returncode == 0,
        'worktree_has_note': '--note' in work,
        'head_has_note': '--note' in head_queue,
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
    diff['fingerprint_ignores'] = sorted(SKIP_FILES)
    return diff


def text_of_changes(project, diff):
    texts = {}
    for relative in diff['added'] + diff['changed']:
        if not (relative.endswith('.md') or 'HANDOFF' in relative or '交接' in Path(relative).name):
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


def stop_process(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        proc.wait(timeout=3)


def start_rollup(project):
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.pop('ROLLUP_PAUSE', None)
    proc = subprocess.Popen(
        [sys.executable, 'jobs/rollup.py'], cwd=project, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    progress = project / 'jobs' / 'rollup-progress.json'
    pid_path = project / 'jobs' / 'rollup.pid'
    deadline = time.time() + 10
    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f'rollup exited early with {proc.returncode}')
            if progress.is_file() and pid_path.is_file():
                payload = json.loads(progress.read_text())
                if payload.get('done') is False:
                    return proc
            time.sleep(0.05)
        raise RuntimeError('rollup did not report in-progress state')
    except Exception:
        stop_process(proc)
        raise


def rollup_state(project, proc):
    progress = project / 'jobs' / 'rollup-progress.json'
    pid_path = project / 'jobs' / 'rollup.pid'
    payload = None
    if progress.is_file():
        try:
            payload = json.loads(progress.read_text())
        except ValueError:
            payload = {}
    pid_alive = False
    if pid_path.is_file():
        try:
            os.kill(int(pid_path.read_text().strip()), 0)
            pid_alive = True
        except (OSError, ValueError):
            pid_alive = False
    return {
        'process_alive': proc.poll() is None,
        'pid_file_alive': pid_alive,
        'done': None if not isinstance(payload, dict) else payload.get('done'),
        'tick': None if not isinstance(payload, dict) else payload.get('tick'),
        'stop_file': (project / 'jobs' / 'rollup-stop').exists(),
    }


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
        'sandbox': job['sandbox'], 'runner_rev': RUNNER_REV,
        'global_note': note['sentence'],
        'isolation': note['user_config_not_used'],
        'resume_sandbox_note': (
            'codex exec resume 没有 --sandbox。第二轮传 -c sandbox_mode，'
            '值是这一题的 followup_sandbox；有没有真的拦住写文件，看 fingerprint。'
        ),
        'fingerprint_note': RUNTIME_NOTE,
        'expected_skill_sha256': varied[job['arm']],
    }
    if job.get('followup'):
        record['followup'] = job['followup']
        record['followup_sandbox'] = job['followup_sandbox']
    if job['kind'] == 'trigger':
        record['expect_skill'] = job['expect_skill']
        record['should_trigger'] = job['should_trigger']
    empty = codex_dir = None
    rollup = None
    try:
        empty, codex_dir = make_codex_homes()
        child_env = codex_child_env(empty, codex_dir)
        with tempfile.TemporaryDirectory(prefix='ytev08-') as temp:
            parent = Path(temp)
            project, names, hashes = prepare(parent, job['fixture'], job['arm'])
            record['installed_skills'] = names
            record['skill_sha256'] = {name: hashes[name] for name in VARIED}
            record['skill_sha256_match'] = record['skill_sha256'] == varied[job['arm']]
            record['shared_skill_sha256'] = {
                name: hashes[name] for name in hashes if name not in VARIED
            }
            if job['fixture'] == 'H2':
                rollup = start_rollup(project)
            try:
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
                    'read_global_three': global_hit,
                    'commands': [command[:400] for command in commands],
                    'event_types': types,
                    'sandbox_hints': hints,
                    'stderr_tail': err,
                    'thread_id': thread,
                    'turn_files': compare(before, after),
                    'git_after_turn': git_facts(project),
                })
                if job.get('followup') and thread and code == 0:
                    mid = snapshot(project)
                    m2, c2, u2, _t2, code2, s2, err2, types2, hints2, _n2, global_hit2 = codex_call(
                        project, job['model'], job['followup'], job['followup_sandbox'],
                        job['id'], 'resume', child_env, resume=thread)
                    end = snapshot(project)
                    follow = compare(mid, end)
                    record.update({
                        'followup_final': m2[-1] if m2 else '',
                        'followup_commentary': m2[:-1],
                        'followup_skills': skills_in(c2),
                        'followup_skill_read_commands': skill_commands(c2),
                        'followup_read_global_three': global_hit2,
                        'followup_commands': [command[:400] for command in c2],
                        'followup_exit': code2,
                        'followup_seconds': s2,
                        'followup_usage': u2,
                        'followup_event_types': types2,
                        'followup_sandbox_hints': hints2,
                        'followup_stderr_tail': err2,
                        'followup_files': follow,
                        'followup_texts': text_of_changes(project, follow),
                        'git_after_followup': git_facts(project),
                    })
                    record['read_global_three'] = bool(record['read_global_three'] or global_hit2)
                elif job.get('followup'):
                    record['followup_exit'] = 'skipped'
                    record['followup_files'] = None
                if rollup is not None:
                    record['rollup'] = rollup_state(project, rollup)
            finally:
                stop_process(rollup)
                rollup = None
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
            replacements = base_replacements(project, parent, empty, codex_dir)
        cleaned = scrub(record, replacements)
        assert_no_secrets(json.dumps(cleaned, ensure_ascii=False))
        return cleaned
    finally:
        stop_process(rollup)
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
                    for arm in ('control', 'treatment'):
                        jobs.append({
                            'id': f'trig-{skill}-{label}{index}-{short_model(model)}-{arm}',
                            'kind': 'trigger', 'case': 'I1', 'fixture': 'I1',
                            'arm': arm, 'model': model, 'rep': 1,
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


def check_setup():
    note = isolation_note()
    print(note['sentence'])
    varied, others = expected_hashes()
    if not all(varied['control'][name] != varied['treatment'][name] for name in VARIED):
        raise SystemExit('the three SKILL.md hashes do not differ')
    load_fixtures()
    codex_template()
    sample = {}
    with tempfile.TemporaryDirectory(prefix='ytev08-check-') as temp:
        parent = Path(temp)
        for fixture in ('H1', 'H2', 'T1', 'T2', 'I1', 'I2'):
            for arm in ('control', 'treatment'):
                case_parent = parent / f'{fixture}-{arm}'
                case_parent.mkdir()
                project, names, hashes = prepare(case_parent, fixture, arm)
                sample.setdefault(arm, hashes)
                print(f'{fixture} {arm} skills={len(names)} commits={git_count(project)}')
        voice_a = (parent / 'T1-control/T1/AGENTS.md').read_text()
        voice_b = (parent / 'T1-treatment/T1/AGENTS.md').read_text()
        if voice_a != voice_b:
            raise SystemExit('voice rules differ between arms')
        for name, digest in others.items():
            if sample['control'][name] != digest or sample['treatment'][name] != digest:
                raise SystemExit(f'shared skill {name} is not the same in both arms')
            if sample['control'][name] != sample['treatment'][name]:
                raise SystemExit(f'shared skill {name} differs between arms')
        h1 = parent / 'H1-control/H1'
        facts = git_facts(h1)
        if not facts['worktree_has_note'] or facts['head_has_note'] or facts['march_tracked'] or not facts['march_ignored']:
            raise SystemExit(f'H1 git state is wrong: {facts}')
        h2_parent = parent / 'H2-check'
        h2_parent.mkdir()
        h2, _names, _hashes = prepare(h2_parent, 'H2', 'control')
        proc = start_rollup(h2)
        try:
            state = rollup_state(h2, proc)
            print(f"H2 rollup done={state['done']} alive={state['process_alive']} stop={state['stop_file']}")
            if state['done'] is not False or not state['process_alive'] or state['stop_file']:
                raise SystemExit(f'H2 rollup self-check failed: {state}')
        finally:
            stop_process(proc)
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_skill_hashes(sample)
    write_json(RESULTS / 'environment.json', scrub({
        **note,
        'skill_md_sha256': varied,
        'shared_skill_md_sha256': others,
        'varied_differ': True,
        'shared_match': True,
    }, base_replacements()))
    print('setup ok')


def write_version_proof():
    proof = None
    for path in sorted(RESULTS.glob('*-control-*.json')):
        try:
            record = json.loads(path.read_text())
        except ValueError:
            continue
        if record.get('status') != 'ok' or record.get('arm') != 'control':
            continue
        read = set(record.get('skills_read') or []) | set(record.get('followup_skills') or [])
        varied_read = sorted(read & set(VARIED))
        if not varied_read:
            continue
        commands = (record.get('skill_read_commands') or []) + (record.get('followup_skill_read_commands') or [])
        if record.get('read_global_three'):
            continue
        expected = record.get('expected_skill_sha256') or {}
        actual = record.get('skill_sha256') or {}
        if not expected or actual != expected:
            continue
        proof = {
            'run_id': record.get('id'),
            'skills_read': record.get('skills_read') or [],
            'followup_skills': record.get('followup_skills') or [],
            'varied_skills_read': varied_read,
            'skill_read_commands': commands,
            'read_global_three': False,
            'skill_sha256': actual,
            'matches_7fb9483': True,
            'sentence': (
                f"{record.get('id')} 的 skills_read 读了项目里的 "
                f"{'、'.join(varied_read)}，命令路径不是全局 ~/.agents/skills，"
                '三个 SKILL.md 的 sha256 等于提交 7fb9483。'
            ),
        }
        break
    if proof is None:
        proof = {
            'matches_7fb9483': False,
            'sentence': '还没有一次成功的对照组运行读到这三个技能的项目副本。',
        }
    write_json(RESULTS / 'version-proof.json', proof)
    print(proof['sentence'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true', help='H1 and T1, both arms, Sol once')
    parser.add_argument('--check-setup', action='store_true', help='Build and install only; no codex call')
    parser.add_argument('--only', help='Comma-separated job ids')
    parser.add_argument('--triggers-only', action='store_true')
    parser.add_argument('--skip-triggers', action='store_true')
    args = parser.parse_args()
    if args.check_setup:
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
    jobs = [] if args.triggers_only else blind_jobs(prompts)
    triggers = [] if args.pilot or args.skip_triggers else trigger_jobs(prompts)
    if args.pilot:
        jobs = [
            job for job in jobs
            if job['case'] in PILOT_CASES and job['model'] == 'gpt-6.1-sol' and job['rep'] == 1
        ]
    if args.only:
        wanted = {item.strip() for item in args.only.split(',') if item.strip()}
        jobs = [job for job in jobs if job['id'] in wanted]
        triggers = [job for job in triggers if job['id'] in wanted]
    print(f'blind {len(jobs)} trigger {len(triggers)} counter {call_count()}', flush=True)
    run_jobs(jobs, note)
    run_jobs(triggers, note)
    write_version_proof()
    print(f'finished counter {call_count()}', flush=True)


if __name__ == '__main__':
    main()
