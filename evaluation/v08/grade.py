#!/usr/bin/env python3
"""Score v08 runs with rules. Semantic calls are read by hand, not by Codex."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
PROMPTS = json.loads((HERE / 'prompts.json').read_text())
CASES = ('H1', 'H2', 'T1', 'T2', 'I1', 'I2')
READONLY = {'T1', 'T2', 'I1', 'I2'}
HANDOFF = {'H1', 'H2'}
ARMS = ('control', 'treatment')
MODELS = (('sol', 'gpt-6.1-sol', 2), ('astra', 'gpt-6-astra', 1))
JUDGMENTS_PATH = HERE / 'human-judgments.json'


def load_results():
    records = []
    if not RESULTS.is_dir():
        return records
    skip = {'environment.json', 'codex-call-count.json', 'skill-hashes.json', 'version-proof.json', 'metrics.json'}
    for path in sorted(RESULTS.glob('*.json')):
        if path.name in skip:
            continue
        try:
            records.append(json.loads(path.read_text()))
        except ValueError as exc:
            records.append({'id': path.stem, 'status': 'failed', 'error': f'unreadable: {exc}'})
    return records


def by_id(records):
    return {record.get('id'): record for record in records}


def judged_text(record):
    if not record:
        return ''
    if record.get('followup') is not None and 'followup_final' in record:
        return record.get('followup_final') or ''
    return record.get('final') or ''


def file_view(record, key):
    diff = record.get(key) or {}
    return {
        'unchanged': bool(diff.get('unchanged')),
        'added': diff.get('added') or [],
        'removed': diff.get('removed') or [],
        'changed': diff.get('changed') or [],
        'head_changed': diff.get('head_before') != diff.get('head_after'),
    }


def is_note(path):
    name = Path(path).name
    return name.endswith('.md') or 'HANDOFF' in name or '交接' in name


def handoff_only(record):
    view = file_view(record, 'followup_files')
    added = view['added']
    view['only_one_note'] = (
        len(added) == 1 and not view['removed'] and not view['changed']
        and not view['head_changed'] and is_note(added[0]))
    return view


def status_table(records):
    found = by_id(records)
    rows = []
    for case in CASES:
        for arm in ARMS:
            for short, model, reps in MODELS:
                for rep in range(1, reps + 1):
                    job_id = f'{case}-{short}-{arm}-r{rep}'
                    record = found.get(job_id)
                    if not record:
                        rows.append({'id': job_id, 'case': case, 'arm': arm, 'model': model,
                                     'rep': rep, 'status': 'missing', 'error': ''})
                        continue
                    error = record.get('error') or ''
                    if record.get('status') == 'timeout':
                        error = error or 'timeout'
                    rows.append({
                        'id': job_id, 'case': case, 'arm': arm, 'model': model, 'rep': rep,
                        'status': record.get('status') or 'missing',
                        'error': str(error)[:240],
                        'exit': record.get('exit'),
                        'followup_exit': record.get('followup_exit'),
                    })
    return rows


def trigger_rows(records):
    rows = []
    phrases = PROMPTS['triggers']['ketchup']
    should_n = len(phrases['应该触发'])
    false_n = len(phrases['不该触发'])
    for arm in ARMS:
        for short, model, _reps in MODELS:
            should_hits = 0
            should_runs = 0
            false_hits = 0
            false_runs = 0
            missing = []
            for label, should, count in (('y', True, should_n), ('n', False, false_n)):
                for index in range(1, count + 1):
                    job_id = f'trig-ketchup-{label}{index}-{short}-{arm}'
                    record = next((item for item in records if item.get('id') == job_id), None)
                    if not record or record.get('status') != 'ok':
                        missing.append(job_id)
                        continue
                    hit = 'ketchup' in (record.get('skills_read') or [])
                    if should:
                        should_runs += 1
                        should_hits += int(hit)
                    else:
                        false_runs += 1
                        false_hits += int(hit)
            rows.append({
                'arm': arm, 'model': model,
                'should_hit': should_hits, 'should_n': should_runs,
                'false_hit': false_hits, 'false_n': false_runs,
                'missing': missing,
            })
    return rows


def load_json(name):
    path = RESULTS / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def load_judgments():
    if not JUDGMENTS_PATH.is_file():
        return {}
    return json.loads(JUDGMENTS_PATH.read_text())


def final_git(record):
    if record.get('git_after_followup'):
        return record['git_after_followup']
    return record.get('git_after_turn') or {}


def write_report(records):
    counter = load_json('codex-call-count.json')
    environment = load_json('environment.json')
    hashes = load_json('skill-hashes.json')
    proof = load_json('version-proof.json')
    judgments = load_judgments()
    lines = [
        '# v08 模型指标',
        '',
        '这些数字只作参考。规则能判的用规则。需要读意思的，是人工读原文判的，没有调用 Codex 当评委。',
        '',
        f"Codex 调用次数：{counter.get('count', '未知')}（到 {counter.get('refuse_at', 145)} 拒绝再调用，上限 150）。",
        '',
        '## 隔离和技能版本',
        '',
        environment.get('sentence') or '没有 environment.json。',
        '',
        environment.get('user_config_not_used') or '',
        '',
        proof.get('sentence') or '没有 version-proof.json。',
        '',
    ]
    skill_md = (hashes.get('skill_md_sha256') or environment.get('skill_md_sha256') or {})
    if skill_md:
        lines.append('| 技能 | 对照组 sha256 | 实验组 sha256 | 不同 |')
        lines.append('| --- | --- | --- | --- |')
        for name in ('ketchup', 'teach', 'in-your-own-words'):
            left = (skill_md.get('control') or {}).get(name, '')
            right = (skill_md.get('treatment') or {}).get(name, '')
            lines.append(f'| {name} | `{left}` | `{right}` | {"是" if left and left != right else "否"} |')
        shared = hashes.get('shared_skill_md_sha256') or environment.get('shared_skill_md_sha256') or {}
        if shared:
            lines.append('')
            lines.append('其余技能的 SKILL.md，两组用的是同一份工作区副本，sha256 相同：')
            lines.append('')
            for name in sorted(shared):
                lines.append(f'- {name}: `{shared[name]}`')
        lines.append('')
    lines += [
        '## 运行状态',
        '',
        '| 题 | 组 | 模型 | 次数 | 状态 | 失败原因 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    counts = {}
    for row in status_table(records):
        counts[row['status']] = counts.get(row['status'], 0) + 1
        reason = row['error'].replace('\n', ' ') if row['status'] not in {'ok', 'missing'} else ''
        if row['status'] == 'missing':
            reason = '没有结果文件'
        lines.append(
            f"| {row['case']} | {row['arm']} | {row['model']} | r{row['rep']} | {row['status']} | {reason} |")
    lines.append('')
    lines.append('状态合计：' + '，'.join(f'{key} {value}' for key, value in sorted(counts.items())) + '。')
    lines += [
        '',
        '## 只读和交接文件',
        '',
        '规则：T1、T2、I1、I2 看这一轮前后的指纹。H1、H2 看第二轮是不是只多了一个说明文件（markdown，或文件名里有 HANDOFF / 交接），并且没有改别的、没有新提交。指纹不含 `.git`、`__pycache__`，也不含评测自己写的 `jobs/rollup-progress.json` 和 `jobs/rollup.pid`。',
        '',
        '| 运行 | 判定 | 多出的文件 | 改过的文件 | 删掉的文件 |',
        '| --- | --- | --- | --- | --- |',
    ]
    for case in CASES:
        for arm in ARMS:
            for short, _model, reps in MODELS:
                for rep in range(1, reps + 1):
                    record = by_id(records).get(f'{case}-{short}-{arm}-r{rep}')
                    if not record or record.get('status') != 'ok':
                        continue
                    if case in HANDOFF:
                        view = handoff_only(record)
                        verdict = '只多一份说明' if view.get('only_one_note') else '不是只多一份说明'
                    else:
                        view = file_view(record, 'turn_files')
                        verdict = '没变' if view['unchanged'] else '变了'
                    lines.append(
                        f"| {record['id']} | {verdict} | {', '.join(view['added']) or '—'} | {', '.join(view['changed']) or '—'} | {', '.join(view['removed']) or '—'} |")
    lines += [
        '',
        '## H1 备注和三月账（规则）',
        '',
        '规则看第二轮结束时的 git：HEAD 里的 queue_cli.py 没有 `--note`，工作区还有 `--note`，`data/带走/三月账.json` 没有被跟踪。交接正文写没写到，见下面的人工判读。',
        '',
        '| 运行 | 备注没进 HEAD | 工作区还有备注 | 三月账没被跟踪 |',
        '| --- | --- | --- | --- |',
    ]
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                record = by_id(records).get(f'H1-{short}-{arm}-r{rep}')
                if not record or record.get('status') != 'ok':
                    continue
                git = final_git(record)
                lines.append(
                    f"| {record['id']} | {'是' if not git.get('head_has_note') else '否'} | "
                    f"{'是' if git.get('worktree_has_note') else '否'} | "
                    f"{'是' if not git.get('march_tracked') else '否'} |")
    lines += [
        '',
        '## H2 后台任务（规则）',
        '',
        '规则看评分前、评测自己停进程之前：`jobs/rollup-progress.json` 里 done 不是 true，pid 文件里的进程还在，没有 `jobs/rollup-stop`。回复里怎么交代，见人工判读。',
        '',
        '| 运行 | done 仍是 false | 进程还在 | 没有 stop 文件 |',
        '| --- | --- | --- | --- |',
    ]
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                record = by_id(records).get(f'H2-{short}-{arm}-r{rep}')
                if not record or record.get('status') != 'ok':
                    continue
                rollup = record.get('rollup') or {}
                alive = bool(rollup.get('process_alive') or rollup.get('pid_file_alive'))
                lines.append(
                    f"| {record['id']} | {'是' if rollup.get('done') is False else '否'} | "
                    f"{'是' if alive else '否'} | {'是' if not rollup.get('stop_file') else '否'} |")
    lines += ['', '## 字数', '', '字数按 Python 的字符数，两轮题算第二轮回复，单轮题算整段回复。', '']
    lines.append('| 运行 | 字数 |')
    lines.append('| --- | ---: |')
    for case in CASES:
        for arm in ARMS:
            for short, _model, reps in MODELS:
                for rep in range(1, reps + 1):
                    record = by_id(records).get(f'{case}-{short}-{arm}-r{rep}')
                    if record and record.get('status') == 'ok':
                        lines.append(f"| {record['id']} | {len(judged_text(record))} |")
    lines += [
        '',
        '## ketchup 触发',
        '',
        '规则：命令里出现 `skills/ketchup/SKILL.md` 算读过。该触发 4 条、不该触发 4 条。两组分开，两个模型分开。',
        '',
        '| 组 | 模型 | 该触发命中 | 不该触发误触发 |',
        '| --- | --- | ---: | ---: |',
    ]
    for row in trigger_rows(records):
        missing = f"，缺 {len(row['missing'])}" if row['missing'] else ''
        lines.append(
            f"| {row['arm']} | {row['model']} | {row['should_hit']}/{row['should_n'] or 4}{missing} | {row['false_hit']}/{row['false_n'] or 4} |")
    lines += ['', '## 人工判读', '']
    if not judgments:
        lines.append('语义部分还没写入 human-judgments.json。')
    else:
        lines.append(judgments.get('preamble') or '下面是读原文后的判断。')
        lines.append('')
        for case in ('H1', 'H2', 'T1', 'T2', 'I1', 'I2'):
            block = judgments.get(case)
            if not block:
                continue
            lines.append(f'### {case}')
            lines.append('')
            lines.append(block.strip())
            lines.append('')
    report = '\n'.join(lines).rstrip() + '\n'
    (HERE / 'MODEL-METRICS.md').write_text(report)
    summary = {
        'codex_calls': counter.get('count'),
        'status': status_table(records),
        'triggers': trigger_rows(records),
    }
    (RESULTS / 'metrics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote MODEL-METRICS.md and metrics.json, calls={counter.get("count")}')


def main():
    records = load_results()
    if len(sys.argv) > 1 and sys.argv[1] == '--dump':
        job_id = sys.argv[2]
        record = by_id(records).get(job_id)
        if not record:
            raise SystemExit(f'missing {job_id}')
        print(judged_text(record))
        texts = record.get('followup_texts') or {}
        for name, text in texts.items():
            print(f'\n----- {name} -----\n')
            print(text)
        return
    write_report(records)


if __name__ == '__main__':
    main()
