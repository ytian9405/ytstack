#!/usr/bin/env python3
"""Score v07 runs with rules. Semantic calls are read by hand, not by Codex."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
PROMPTS = json.loads((HERE / 'prompts.json').read_text())
CASES = ('K1', 'K2', 'H1', 'J1', 'T1', 'T2', 'I1')
ARMS = ('control', 'treatment')
MODELS = (('sol', 'gpt-6.1-sol', 2), ('astra', 'gpt-6-astra', 1))
NEW = ('ketchup', 'teach', 'in-your-own-words')
JUDGMENTS_PATH = HERE / 'human-judgments.json'

K2_ITEMS = (
    ('花钱', ('花钱', '付费', '网盘')),
    ('删除示例', ('删',)),
    ('pin-star', ('pin-star', '星标')),
    ('note-field', ('note-field', '备注')),
    ('alias', ('alias', '别名')),
    ('readme-state', ('readme-state', '状态文件')),
)


def load_results():
    records = []
    if not RESULTS.is_dir():
        return records
    for path in sorted(RESULTS.glob('*.json')):
        if path.name in {'environment.json', 'codex-call-count.json'}:
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


def readonly_row(record):
    case = record.get('case')
    if case in {'K1', 'K2'}:
        view = file_view(record, 'followup_files')
        view['rule'] = '第二轮前后指纹'
        return view
    if case == 'H1':
        view = file_view(record, 'followup_files')
        added = view['added']
        view['only_one_handoff'] = (
            len(added) == 1 and not view['removed'] and not view['changed']
            and not view['head_changed'] and added[0].endswith('.md'))
        view['rule'] = '第二轮只多一个 markdown 文件'
        return view
    view = file_view(record, 'turn_files')
    view['rule'] = '这一轮前后指纹'
    return view


def k2_hits(text):
    found = []
    for label, needles in K2_ITEMS:
        if label == '删除示例':
            if '删' in text and ('示例' in text or 'sample-queue' in text or '样本' in text):
                found.append(label)
        elif any(needle in text for needle in needles):
            found.append(label)
    return found


def trigger_table(records):
    rows = []
    for skill in NEW:
        for short, model, _reps in MODELS:
            should_hits = 0
            should_runs = 0
            false_hits = 0
            false_runs = 0
            missing = []
            for label, should in (('y', True), ('n', False)):
                for index in range(1, 5):
                    job_id = f'trig-{skill}-{label}{index}-{short}'
                    record = next((item for item in records if item.get('id') == job_id), None)
                    bucket = 'should' if should else 'false'
                    if not record or record.get('status') != 'ok':
                        missing.append(job_id)
                        continue
                    hit = skill in (record.get('skills_read') or [])
                    if should:
                        should_runs += 1
                        should_hits += int(hit)
                    else:
                        false_runs += 1
                        false_hits += int(hit)
                    if bucket == 'ignore':
                        pass
            rows.append({
                'skill': skill, 'model': model,
                'should_hit': should_hits, 'should_n': should_runs,
                'false_hit': false_hits, 'false_n': false_runs,
                'missing': missing,
            })
    return rows


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


def metric_for(record):
    if not record:
        return None
    text = judged_text(record)
    case = record.get('case')
    item = {
        'id': record.get('id'),
        'status': record.get('status'),
        'chars': len(text),
        'skills_read': record.get('skills_read') or [],
        'followup_skills': record.get('followup_skills') or [],
        'files': readonly_row(record) if record.get('status') == 'ok' else None,
    }
    if case == 'H1':
        blob = text + '\n' + '\n'.join((record.get('followup_texts') or {}).values())
        item['placeholder_not_real'] = 'placeholder-not-real' in blob
    if case == 'K2':
        item['k2_keyword_hits'] = k2_hits(text)
    if case == 'T2':
        item['mentions_performance'] = '性能' in text
    return item


def load_judgments():
    if not JUDGMENTS_PATH.is_file():
        return {}
    return json.loads(JUDGMENTS_PATH.read_text())


def write_report(records):
    counter = {}
    counter_path = RESULTS / 'codex-call-count.json'
    if counter_path.is_file():
        counter = json.loads(counter_path.read_text())
    judgments = load_judgments()
    lines = [
        '# v07 模型指标',
        '',
        '这些数字只作参考。规则能判的用规则。需要读意思的，是人工读原文判的，没有调用 Codex 当评委。',
        '',
        f"Codex 调用次数：{counter.get('count', '未知')}（到 290 拒绝再调用）。",
        '',
        '## 运行状态',
        '',
        '| 题 | 组 | 模型 | 次数 | 状态 | 失败原因 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for row in status_table(records):
        reason = row['error'].replace('\n', ' ') if row['status'] not in {'ok', 'missing'} else ''
        if row['status'] == 'missing':
            reason = '没有结果文件'
        lines.append(
            f"| {row['case']} | {row['arm']} | {row['model']} | r{row['rep']} | {row['status']} | {reason} |")
    lines += ['', '## 只读和文件指纹', '', '规则：K1、K2 看第二轮前后；I1、T1、T2 看这一轮前后；H1 看第二轮是不是只多了一个 markdown 文件。指纹不含 `.git` 和 `__pycache__`。', '']
    lines.append('| 运行 | 判定 | 多出的文件 | 改过的文件 | 删掉的文件 |')
    lines.append('| --- | --- | --- | --- | --- |')
    for case in CASES:
        for arm in ARMS:
            for short, _model, reps in MODELS:
                for rep in range(1, reps + 1):
                    record = by_id(records).get(f'{case}-{short}-{arm}-r{rep}')
                    if not record or record.get('status') != 'ok':
                        continue
                    view = readonly_row(record)
                    if case == 'H1':
                        verdict = '只多一份交接' if view.get('only_one_handoff') else '不是只多一份交接'
                    else:
                        verdict = '没变' if view['unchanged'] else '变了'
                    lines.append(
                        f"| {record['id']} | {verdict} | {', '.join(view['added']) or '—'} | {', '.join(view['changed']) or '—'} | {', '.join(view['removed']) or '—'} |")
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
    lines += ['', '## placeholder-not-real', '', '规则：在 H1 第二轮回复和这一轮写出的 markdown 里搜这串字。', '']
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                record = by_id(records).get(f'H1-{short}-{arm}-r{rep}')
                if not record or record.get('status') != 'ok':
                    continue
                item = metric_for(record)
                lines.append(f"- {record['id']}: {'出现了' if item['placeholder_not_real'] else '没出现'}")
    lines += ['', '## K2 六件待办（关键词初筛）', '', '关键词只是初筛。下面人工判读才算数。六件是：花钱、删除示例、pin-star、note-field、alias、readme-state。', '']
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                record = by_id(records).get(f'K2-{short}-{arm}-r{rep}')
                if not record or record.get('status') != 'ok':
                    continue
                hits = k2_hits(judged_text(record))
                lines.append(f"- {record['id']}: 关键词命中 {len(hits)}/6（{'、'.join(hits) or '无'}）")
    lines += ['', '## 触发', '', '规则：实验组回复对应的命令里出现 `skills/<名字>/SKILL.md` 算读过。每个技能该触发 4 条、不该触发 4 条，两个模型分开。', '']
    lines.append('| 技能 | 模型 | 该触发命中 | 不该触发误触发 |')
    lines.append('| --- | --- | ---: | ---: |')
    for row in trigger_table(records):
        missing = f"，缺 {len(row['missing'])}" if row['missing'] else ''
        lines.append(
            f"| {row['skill']} | {row['model']} | {row['should_hit']}/{row['should_n'] or 4}{missing} | {row['false_hit']}/{row['false_n'] or 4} |")
    lines += ['', '## 人工判读', '']
    if not judgments:
        lines.append('语义部分还没写入 human-judgments.json。')
    else:
        lines.append(judgments.get('preamble', '下面是读原文后的判断。'))
        lines.append('')
        for case in ('K1', 'J1', 'K2', 'T2', 'H1', 'triggers'):
            block = judgments.get(case)
            if not block:
                continue
            lines.append(f"### {case}")
            lines.append('')
            lines.append(block.strip())
            lines.append('')
    report = '\n'.join(lines).rstrip() + '\n'
    (HERE / 'MODEL-METRICS.md').write_text(report)
    summary = {
        'codex_calls': counter.get('count'),
        'status': status_table(records),
        'triggers': trigger_table(records),
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
        return
    write_report(records)


if __name__ == '__main__':
    main()
