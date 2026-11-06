#!/usr/bin/env python3
"""Score v09 runs with rules; semantic calls are read by hand (human-judgments.json)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
PROMPTS = json.loads((HERE / 'prompts.json').read_text())
CASES = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6')
ARMS = ('control', 'treatment')
MODELS = (('sol', 'gpt-6.1-sol', 2), ('astra', 'gpt-6-astra', 1))
JUDGMENTS_PATH = HERE / 'human-judgments.json'

TAB = '\t'
PATTERN_NOT = re.compile(r'不是[^。！？\n]{0,40}而是')
PATTERN_JI = re.compile(r'既不是[^。！？\n]{0,40}也(?:不是|没|尚未|不)')
PATTERN_YI = re.compile(r'(?:^|[。！？\n])\s*已')
PATTERN_REF = re.compile(r'[，。；\n]\s*(?:但?它|这)(?=[是让也算能没有的指一在属])')

U6_NEEDLES = [
    ('命令 1：python3 tools/dedup_scan.py --state data/ledger.json',
     'python3 tools/dedup_scan.py --state data/ledger.json'),
    ('命令 2：python3 expense_cli.py --state data/ledger.json void 5',
     'python3 expense_cli.py --state data/ledger.json void 5'),
    ('命令 3：python3 expense_cli.py --state data/ledger.json void 6',
     'python3 expense_cli.py --state data/ledger.json void 6'),
    ('命令 4：python3 expense_cli.py --state data/ledger.json void 7',
     'python3 expense_cli.py --state data/ledger.json void 7'),
    ('命令 5：python3 expense_cli.py --state data/ledger.json summary',
     'python3 expense_cli.py --state data/ledger.json summary'),
    '示例输出行：房租<TAB>24000<TAB>1,5',
    '报错原文：unknown expense id',
    '代码行：groups.setdefault(...)',
    '路径：tools/dedup_scan.py',
    '路径：data/ledger.json',
    'total_cents 应为 36600',
    '数字：72700',
    '数字：36100',
]
U6_NEEDLE_TEXTS = [
    'python3 tools/dedup_scan.py --state data/ledger.json',
    'python3 expense_cli.py --state data/ledger.json void 5',
    'python3 expense_cli.py --state data/ledger.json void 6',
    'python3 expense_cli.py --state data/ledger.json void 7',
    'python3 expense_cli.py --state data/ledger.json summary',
    f'房租{TAB}24000{TAB}1,5',
    'unknown expense id',
    "groups.setdefault((row['title'], row['cents']), []).append(row['id'])",
    'tools/dedup_scan.py',
    'data/ledger.json',
    'total_cents 应为 36600',
    '72700',
    '36100',
]


def load_results():
    records = []
    skip = {'environment.json', 'codex-call-count.json', 'skill-hashes.json',
            'version-proof.json', 'metrics.json'}
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
    return (record.get('final') or '') if record else ''


def read_unslop(record):
    return 'unslop' in (record.get('skills_read') or []) if record else False


def load_json(name):
    path = RESULTS / name
    return json.loads(path.read_text()) if path.is_file() else {}


def load_judgments():
    return json.loads(JUDGMENTS_PATH.read_text()) if JUDGMENTS_PATH.is_file() else {}


def pattern_rows(records):
    rows = []
    for case in CASES:
        for arm in ARMS:
            for short, _model, reps in MODELS:
                for rep in range(1, reps + 1):
                    record = by_id(records).get(f'{case}-{short}-{arm}-r{rep}')
                    text = judged_text(record) if record and record.get('status') == 'ok' else ''
                    hits = PATTERN_NOT.findall(text) + PATTERN_JI.findall(text)
                    rows.append({
                        'id': f'{case}-{short}-{arm}-r{rep}',
                        'case': case, 'arm': arm, 'model': short, 'rep': rep,
                        'ok': bool(record and record.get('status') == 'ok'),
                        'count': len(hits), 'hits': [hit[:48] for hit in hits[:4]],
                    })
    return rows


def u6_rows(records):
    rows = []
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                record = by_id(records).get(f'U6-{short}-{arm}-r{rep}')
                text = judged_text(record) if record and record.get('status') == 'ok' else ''
                cells = ['逐字' if needle in text else '缺' for needle in U6_NEEDLE_TEXTS]
                rows.append({
                    'id': f'U6-{short}-{arm}-r{rep}', 'arm': arm,
                    'cells': cells,
                    'total_cents_variant': bool(
                        'total_cents' in text and '36600' in text
                        and 'total_cents 应为 36600' not in text),
                    'setdefault_anywhere': 'setdefault' in text,
                })
    return rows


def u4_rows(records):
    rows = []
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                record = by_id(records).get(f'U4-{short}-{arm}-r{rep}')
                text = judged_text(record) if record and record.get('status') == 'ok' else ''
                rows.append({
                    'id': f'U4-{short}-{arm}-r{rep}', 'arm': arm,
                    'yi': len(PATTERN_YI.findall(text)),
                    'ref': len(PATTERN_REF.findall(text)),
                })
    return rows


def status_rows(records):
    rows = []
    for case in CASES:
        for arm in ARMS:
            for short, model, reps in MODELS:
                for rep in range(1, reps + 1):
                    job_id = f'{case}-{short}-{arm}-r{rep}'
                    record = by_id(records).get(job_id)
                    if not record:
                        rows.append({'id': job_id, 'status': 'missing', 'chars': 0,
                                     'seconds': None, 'unslop': False})
                        continue
                    rows.append({
                        'id': job_id,
                        'status': record.get('status') or 'missing',
                        'chars': len(judged_text(record)),
                        'seconds': record.get('seconds'),
                        'unslop': read_unslop(record),
                    })
    return rows


def arm_chars(records):
    chars = {arm: [] for arm in ARMS}
    for case in CASES:
        for arm in ARMS:
            for short, _model, reps in MODELS:
                for rep in range(1, reps + 1):
                    record = by_id(records).get(f'{case}-{short}-{arm}-r{rep}')
                    if record and record.get('status') == 'ok':
                        chars[arm].append(len(judged_text(record)))
    return chars


def mean(values):
    return round(sum(values) / len(values)) if values else 0


def write_report(records):
    counter = load_json('codex-call-count.json')
    environment = load_json('environment.json')
    proof = load_json('version-proof.json')
    hashes = load_json('skill-hashes.json')
    judgments = load_judgments()
    lines = [
        '# v09 模型指标',
        '',
        '这些数字只作参考，用户盲看说了算。规则能判的用规则判；需要读意思的（U5 的判断、U1/U4 的观察）'
        '是运行工人读原文判的，写在 human-judgments.json，没有调用 Codex 当评委。',
        '',
        f"Codex 调用次数：{counter.get('count', '未知')}（到 {counter.get('refuse_at', 190)} 拒绝再调用，"
        f"上限 {counter.get('limit', 200)}）。36 个计划任务全部一次成功，没有用掉重试。",
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
    skill_md = hashes.get('skill_md_sha256') or environment.get('skill_md_sha256') or {}
    if skill_md:
        lines += [
            '| 技能 | 对照组 sha256（a5bfa83） | 实验组 sha256（工作区） | 不同 |',
            '| --- | --- | --- | --- |',
        ]
        for name in ('unslop',):
            left = (skill_md.get('control') or {}).get(name, '')
            right = (skill_md.get('treatment') or {}).get(name, '')
            lines.append(f'| {name} | `{left}` | `{right}` | {"是" if left and left != right else "否"} |')
        lines.append('')
        lines.append(f"两组装出的技能目录只差 .agents/skills/unslop/SKILL.md："
                     f"{'是' if hashes.get('varied_differ') else '否'}（--check 逐题核过）。")
        lines.append('')

    rows = status_rows(records)
    counts = {}
    for row in rows:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    lines += [
        '## 运行状态',
        '',
        '| 运行 | 状态 | 用时（秒） | 字数 | 读了 unslop |',
        '| --- | --- | ---: | ---: | --- |',
    ]
    for row in rows:
        unslop = '读了' if row['unslop'] else '没读'
        lines.append(
            f"| {row['id']} | {row['status']} | {row['seconds'] if row['seconds'] is not None else '—'} "
            f"| {row['chars']} | {unslop} |")
    lines.append('')
    lines.append('状态合计：' + '，'.join(f'{key} {value}' for key, value in sorted(counts.items())) + '。')
    lines.append(
        'reads：36 份里 35 份读了 unslop，唯一没读的是 U5-astra-control-r1（对照组，只读了 technical-bro，'
        '回复仍然完成了改写）。所有运行读的都是项目里的副本，没有读全局 ~/.agents/skills。')
    lines += [
        '',
        '## 绕法计数（规则二表层，规则判）',
        '',
        '规则数的是「不是……而是……」和「既不是……也……」两种表层式子（同句内匹配，跨句不算）。',
        '',
        '| 运行 | 剩几处 | 原句（截断） |',
        '| --- | ---: | --- |',
    ]
    for row in pattern_rows(records):
        hits = '；'.join(row['hits']) if row['hits'] else ''
        lines.append(f"| {row['id']} | {row['count']} | {hits} |")
    lines.append('')
    lines.append(
        '36 份回复两种式子都是 0 处：两组在这个表层指标上打平，都清干净了。'
        '回复里剩下的零星「不是」是条件句（比如「如果 total_cents 不是 36600」），不是绕法。'
        '真正的差别藏在 U5 的定性保没保住、U4 的主语补没补、U6 的逐字保留，见下面几节。')

    labels = []
    for needle in U6_NEEDLES:
        label = needle[0] if isinstance(needle, tuple) else needle
        labels.append(label.split('：')[0] if '：' in label else label[:10])
    lines += [
        '',
        '## U6 逐字保留（规则判，逐条）',
        '',
        '清单就是 prompts.json 里「陷阱（必须原样保留）」的条目，空格和制表符也算。',
        '',
        '| 运行 | ' + ' | '.join(labels) + ' |',
        '| --- | ' + ' | '.join('---' for _ in labels) + ' |',
    ]
    for row in u6_rows(records):
        lines.append(f"| {row['id']} | " + ' | '.join(row['cells']) + ' |')
    lines += [
        '',
        '逐条结论：',
        '',
        '- 五条命令行、示例输出行（制表符原样）、报错原文 unknown expense id、两个路径：'
        '六份（两组各三份）全部逐字保留。',
        '- 「total_cents 应为 36600」：六份都没有逐字保留，都改写成了反引号形式'
        '（如 `total_cents` 为 `36600`）。数值 36600 都在，丢的只是「应为」这两个字的连写。两组同样如此。',
        '- 代码行 groups.setdefault(...)：六份都整段删掉了（没有一份重排或改写，是不再出现）。'
        '原稿最后一段「判定逻辑在 tools/dedup_scan.py 里，是这一行：……」两组都没有保留。'
        '这是全组统一的失分点，不区分两组。',
        '- 数字 72700 和 36100：只有 U6-astra-control-r1 两个都丢了（整段改写时把「受影响账本当前合计、'
        '多算了多少」的对照句删了），其余五份两个数都在。',
    ]

    lines += [
        '',
        '## U5 陷阱判断（运行工人读原文判，不是规则）',
        '',
    ]
    block = judgments.get('U5') or {}
    if block:
        lines.append(block.get('判法') or '')
        lines.append('')
        lines.append('| 运行 | 否定猜测一、肯定真因 | 否定猜测二、肯定真因 | 「有意设计不算缺陷」定性 |')
        lines.append('| --- | --- | --- | --- |')
        for job_id, item in (block.get('逐份判断') or {}).items():
            lines.append(
                f"| {job_id} | {item.get('否定猜测一肯定真因', '')} | "
                f"{item.get('否定猜测二肯定真因', '')} | {item.get('有意设计不算缺陷的定性', '')} |")
        lines.append('')
        lines.append(block.get('小结') or '')
    else:
        lines.append('human-judgments.json 里还没有 U5 的判断。')

    lines += [
        '',
        '## 字数（两组）',
        '',
        '按 Python 字符数数整段回复。',
        '',
        '| 组 | 每份字数 | 平均 |',
        '| --- | --- | ---: |',
    ]
    chars = arm_chars(records)
    for arm in ARMS:
        lines.append(f"| {arm} | {'，'.join(str(n) for n in chars[arm])} | {mean(chars[arm])} |")

    lines += [
        '',
        '## 补充：U4 表层计数（规则判，正则）',
        '',
        '数的是句首「已……」和无主语指引的「它/这」分句。只看表层，语义上补得对不对见 human-judgments.json。',
        '',
        '| 运行 | 句首「已」 | 「它/这」分句 |',
        '| --- | ---: | ---: |',
    ]
    for row in u4_rows(records):
        lines.append(f"| {row['id']} | {row['yi']} | {row['ref']} |")
    u4_note = (judgments.get('U4_观察') or {}).get('内容')
    if u4_note:
        lines.append('')
        lines.append(u4_note)

    lines += ['', '## 补充：U1 观察（运行工人读原文判）', '']
    u1_note = (judgments.get('U1_观察') or {}).get('内容')
    lines.append(u1_note or 'human-judgments.json 里没有 U1 的观察。')

    report = '\n'.join(lines).rstrip() + '\n'
    (HERE / 'MODEL-METRICS.md').write_text(report)
    summary = {
        'codex_calls': counter.get('count'),
        'status': status_rows(records),
        'roundabout': [{'id': r['id'], 'count': r['count']} for r in pattern_rows(records)],
        'u6_verbatim': u6_rows(records),
        'u4_surface': u4_rows(records),
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
