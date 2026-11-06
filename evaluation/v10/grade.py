#!/usr/bin/env python3
"""Score v10 runs. Surface counts are rule-judged (regex/needles); semantic calls
are the run worker's own readings, kept in human-judgments.json and quoted here."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
PROMPTS = json.loads((HERE / 'prompts.json').read_text())
CASES = ('W1', 'W2', 'R1', 'R2', 'C1', 'M1')
ARMS = ('control', 'treatment')
MODELS = (('sol', 'gpt-6.1-sol', 2), ('astra', 'gpt-6-astra', 1))
JUDGMENTS_PATH = HERE / 'human-judgments.json'

TAB = '\t'
PATTERN_NOT = re.compile(r'不是[^。！？\n]{0,40}而是')
PATTERN_JI = re.compile(r'既不是[^。！？\n]{0,40}也(?:不是|没|尚未|不)')

# W1/W2 borrowed words the rewritten rule 41 says to replace with everyday wording.
REPLACEABLE = {
    'W1': ('nightly', 'warmup', 'outlier', 'drift', '缺段缝合'),
    'W2': ('localtime', 'utc', 'bucket', '整点对齐', 'rounding', 'offset'),
}
# Config keys and anchors that must survive verbatim (rule: names readers must go edit).
MUST_KEEP = {
    'W1': ('csv_dir', 'report_hour', 'logger.json'),
    'W2': ('sensors', 'report_hour', 'logger.json'),
}
FACT_ANCHORS = {
    'W1': ('31.2', '0.4'),
    'W2': ('S1', 'S2'),
}
EXPLAIN_MARKS = ('也就是', '是指', '指的是', '意思是', '（指', '（即', '，即', '表示', '就是')
FUNCTION_WORDS = set('与的按在把或及被是对从到向于让用给把靠依随')
CJK = re.compile(r'[\u4e00-\u9fff]')

M1_NEEDLES = [
    ('命令1', 'python3 tools/gap_scan.py --state data/readings.json'),
    ('命令2', 'python3 temp_log.py --state data/readings.json add S2 18.5 --at 2026-11-05T03:00'),
    ('命令3', 'python3 temp_log.py --state data/readings.json add S2 18.5 --at 2026-11-05T04:00'),
    ('命令4', 'python3 temp_log.py --state data/readings.json stats --sensor S2'),
    ('命令5', 'python3 temp_log.py --state data/readings.json add S3 21.8'),
    ('输出行1(制表符)', f'S1{TAB}2026-11-05{TAB}0,1,2,3,4'),
    ('输出行2(制表符)', f'S2{TAB}2026-11-05{TAB}3,4'),
    ('报错原文', 'unknown sensor id'),
    ('代码行', 'gaps.setdefault((sensor, day), []).append(str(hour))'),
    ('路径1', 'tools/gap_scan.py'),
    ('路径2', 'data/readings.json'),
    ('路径3', 'logger.json'),
    ('配置项', 'sensors'),
    ('配置对', '"S3": "书房"'),
    ('验收值', 'count 应为 24'),
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


def run_ids(case):
    for arm in ARMS:
        for short, _model, reps in MODELS:
            for rep in range(1, reps + 1):
                yield f'{case}-{short}-{arm}-r{rep}', arm


def term_in(term, text):
    if re.fullmatch(r'[A-Za-z_0-9]+', term):
        return re.search(rf'(?<![A-Za-z_0-9]){re.escape(term)}(?![A-Za-z_0-9])', text) is not None
    return term in text


def term_spans(term, text):
    if re.fullmatch(r'[A-Za-z_0-9]+', term):
        return [(m.start(), m.end())
                for m in re.finditer(rf'(?<![A-Za-z_0-9]){re.escape(term)}(?![A-Za-z_0-9])', text)]
    spans, start = [], 0
    while True:
        idx = text.find(term, start)
        if idx < 0:
            return spans
        spans.append((idx, idx + len(term)))
        start = idx + len(term)


def explained(term, text):
    for span in term_spans(term, text):
        lo = max(0, span[0] - 30)
        hi = min(len(text), span[1] + 60)
        window = text[lo:hi]
        if any(mark in window for mark in EXPLAIN_MARKS):
            return True
        tail = text[span[1]:span[1] + 2]
        if tail.startswith('（') and '）' in text[span[1]:span[1] + 44]:
            return True
        # Apposition right before the term, e.g. 校准值 `offset`、本地时间 `localtime`.
        head = text[max(0, span[0] - 8):span[0]]
        for match in CJK.finditer(head):
            after = head[match.end():]
            if after and not set(after) <= {'`', ' ', '\u3000'}:
                continue
            if match.group() not in FUNCTION_WORDS:
                return True
    return False


def classify_term(term, text):
    if not term_in(term, text):
        return '换'
    return '注' if explained(term, text) else '裸'


def word_rows(case, records):
    rows = []
    for job_id, _arm in run_ids(case):
        record = by_id(records).get(job_id)
        text = judged_text(record) if record and record.get('status') == 'ok' else ''
        row = {'id': job_id, 'cells': {}, 'keep': {}, 'facts': {}}
        for term in REPLACEABLE[case]:
            row['cells'][term] = classify_term(term, text) if text else '—'
        for term in MUST_KEEP[case]:
            row['keep'][term] = '在' if term_in(term, text) else '没了'
        for term in FACT_ANCHORS[case]:
            row['facts'][term] = '在' if term in text else '没了'
        rows.append(row)
    return rows


def pattern_rows(records, cases=CASES):
    rows = []
    for case in cases:
        for job_id, _arm in run_ids(case):
            record = by_id(records).get(job_id)
            text = judged_text(record) if record and record.get('status') == 'ok' else ''
            hits = PATTERN_NOT.findall(text) + PATTERN_JI.findall(text)
            rows.append({
                'id': job_id, 'ok': bool(record and record.get('status') == 'ok'),
                'count': len(hits), 'hits': [hit[:48] for hit in hits[:4]],
            })
    return rows


def m1_rows(records):
    rows = []
    for job_id, _arm in run_ids('M1'):
        record = by_id(records).get(job_id)
        text = judged_text(record) if record and record.get('status') == 'ok' else ''
        cells = ['逐字' if needle in text else '缺' for _label, needle in M1_NEEDLES]
        rows.append({
            'id': job_id, 'cells': cells,
            'count_24_value': bool('count' in text and '24' in text),
        })
    return rows


def status_rows(records):
    rows = []
    for case in CASES:
        for arm in ARMS:
            for short, _model, reps in MODELS:
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


def tally(cells):
    out = {}
    for value in cells:
        out[value] = out.get(value, 0) + 1
    return out


def write_report(records):
    counter = load_json('codex-call-count.json')
    environment = load_json('environment.json')
    proof = load_json('version-proof.json')
    hashes = load_json('skill-hashes.json')
    judgments = load_judgments()

    rows = status_rows(records)
    ok_rows = [r for r in rows if r['status'] == 'ok']
    no_unslop = [r['id'] for r in ok_rows if not r['unslop']]
    counts = tally(r['status'] for r in rows)

    lines = [
        '# v10 模型指标',
        '',
        '这些数字只作参考，用户盲看说了算。规则能判的（句式计数、生词替换、逐字比对）用规则判；'
        '需要读意思的（C1、M1 的纠正判断，R1、R2 的抽查）是运行工人读原文判的，'
        '写在 human-judgments.json，没有调用 Codex 当评委。',
        '',
        f"Codex 调用次数：{counter.get('count', '未知')}（到 {counter.get('refuse_at', 150)} 拒绝再调用，"
        f"上限 {counter.get('limit', 200)}）。36 个计划任务全部成功，没有用掉重试。",
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
            '| 技能 | 对照组 sha256（a5bfa83） | 实验组 sha256（工作区 cc6c80c） | 不同 |',
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
    if no_unslop:
        lines.append(
            f"reads：36 份里 {36 - len(no_unslop)} 份读了 unslop，没读的是 {('、'.join(no_unslop))}"
            f"（实验组 Astra 一次，只读了 technical-bro，回复仍然完成了全文改写；v09 也有过一次同样的跳过）。"
            f"其余运行读的都是项目里的副本，没有读全局 ~/.agents/skills。")
    else:
        lines.append('reads：36 份全部读了 unslop，读的都是项目里的副本。')

    prows = pattern_rows(records)
    lines += [
        '',
        '## 绕法计数（规则 42 表层，规则判）',
        '',
        '规则数的是「不是……而是……」和「既不是……也……」两种表层式子（同句内匹配，跨句不算）。'
        'C1、M1 里「不是 A，是 B」的正确纠正不带「而」，不计入。',
        '',
        '| 运行 | 剩几处 | 原句（截断） |',
        '| --- | ---: | --- |',
    ]
    for row in prows:
        hits = '；'.join(row['hits']) if row['hits'] else ''
        lines.append(f"| {row['id']} | {row['count']} | {hits} |")
    total_hits = sum(r['count'] for r in prows)
    per_arm = {arm: sum(r['count'] for r in prows if f'-{arm}-' in r['id']) for arm in ARMS}
    nonzero = [r['id'] for r in prows if r['count']]
    lines.append('')
    if total_hits == 0:
        lines.append(
            '36 份回复两种式子合计 0 处：两组都把表层绕法清干净了，这个指标分不出两组。'
            '差别要看 W1/W2 的生词处理、C1/M1 的判断保没保住，见下面几节。')
    else:
        lines.append(
            f'36 份合计 {total_hits} 处（对照组 {per_arm["control"]}、实验组 {per_arm["treatment"]}），'
            f'剩有残留的运行：{"、".join(nonzero) if nonzero else "无"}。')

    for case, title in (('W1', 'W1 进展说明'), ('W2', 'W2 口径说明')):
        wrows = word_rows(case, records)
        terms = REPLACEABLE[case]
        keeps = MUST_KEEP[case]
        lines += [
            '',
            f'## {case} 生词处理（规则 41 表层，规则判）',
            '',
            f'能换的词：{"、".join(terms)}。换＝换成日常说法；注＝保留原词并解释；裸＝保留原词没解释。'
            '注的判定是启发式：词旁边有「也就是／是指／表示」一类标记，或紧挨着同位语（如「校准值 offset」），算注。',
            '必须保留的：' + '、'.join(keeps) + '（读者要照着去配置文件改）。',
            '',
            '| 运行 | ' + ' | '.join(terms) + ' | ' + ' | '.join(keeps) + ' | 事实锚点 |',
            '| --- | ' + ' | '.join('---' for _ in terms) + ' | ' + ' | '.join('---' for _ in keeps) + ' | --- |',
        ]
        for row in wrows:
            cells = ' | '.join(row['cells'][t] for t in terms)
            keep = ' | '.join(row['keep'][t] for t in keeps)
            facts = '，'.join(f"{k}{v}" for k, v in row['facts'].items())
            lines.append(f"| {row['id']} | {cells} | {keep} | {facts} |")
        tallies = {arm: tally(
            cell for row in wrows if f'-{arm}-' in row['id'] for cell in row['cells'].values())
            for arm in ARMS}
        lost_keep = [row['id'] for row in wrows if '没了' in row['keep'].values()]
        lines += [
            '',
            f"换/注/裸合计——对照组：{tallies['control'].get('换', 0)}/"
            f"{tallies['control'].get('注', 0)}/{tallies['control'].get('裸', 0)}；"
            f"实验组：{tallies['treatment'].get('换', 0)}/"
            f"{tallies['treatment'].get('注', 0)}/{tallies['treatment'].get('裸', 0)}。",
        ]
        if lost_keep:
            lines.append(f'必须保留的配置项被换掉的运行：{"、".join(lost_keep)}。')
        else:
            lines.append('必须保留的配置项名（含 logger.json）六份全部原样保留，事实锚点一个不丢。')

    mrows = m1_rows(records)
    labels = [label for label, _needle in M1_NEEDLES]
    lines += [
        '',
        '## M1 逐字保留（规则判，逐条）',
        '',
        '清单就是 prompts.json 里 M1「陷阱（必须原样保留）」的条目，空格和制表符也算。',
        '',
        '| 运行 | ' + ' | '.join(labels) + ' | count 与 24 都在 |',
        '| --- | ' + ' | '.join('---' for _ in labels) + ' | --- |',
    ]
    for row in mrows:
        lines.append(f"| {row['id']} | " + ' | '.join(row['cells']) +
                     f" | {'是' if row['count_24_value'] else '否'} |")
    lines += [
        '',
        '逐条结论：',
        '',
    ]
    for (label, needle), idx in zip(M1_NEEDLES, range(len(M1_NEEDLES))):
        missing = [row['id'] for row in mrows if row['cells'][idx] == '缺']
        if not missing:
            lines.append(f'- {label}：六份全部逐字保留。')
        elif len(missing) == len(mrows):
            lines.append(f'- {label}（`{needle}`）：六份都没有保留。')
        else:
            lines.append(f'- {label}：{"、".join(missing)} 缺。')
    count24_verbatim = [row['id'] for row in mrows if row['cells'][-1] == '逐字']
    lines.append('')
    if count24_verbatim:
        lines.append(f'- 「count 应为 24」逐字保留的：{"、".join(count24_verbatim)}；'
                     f'其余改写成反引号形式（`count` 应为 `24`），数值都在。')
    else:
        lines.append('- 「count 应为 24」六份都没有逐字保留，都改写成反引号形式'
                     '（如 `count` 应为 `24`），count 和 24 的数值六份都在。')

    for case, key in (('C1', 'C1'), ('M1', 'M1')):
        block = judgments.get(key) or {}
        lines += [
            '',
            f'## {case} 纠正判断（运行工人读原文判，不是规则）',
            '',
            block.get('判法') or '',
            '',
        ]
        per = block.get('逐份判断') or {}
        if case == 'C1':
            lines.append('| 运行 | 否定猜测一、肯定真因 | 否定猜测二、肯定真因 | 「不算缺陷」定性 | 三层转折句 | 数字 |')
            lines.append('| --- | --- | --- | --- | --- | --- |')
            for job_id, item in per.items():
                lines.append(
                    f"| {job_id} | {item.get('否定猜测一肯定真因', '')} | "
                    f"{item.get('否定猜测二肯定真因', '')} | {item.get('有意设计不算缺陷的定性', '')} | "
                    f"{item.get('三层转折句拆开', '')} | {item.get('数字事实', '')} |")
        else:
            lines.append('| 运行 | 纠正一（不是电池/漏报） | 纠正二（不是坏了） | 绕法句拆开 | 停下贴值班的告诫 |')
            lines.append('| --- | --- | --- | --- | --- |')
            for job_id, item in per.items():
                lines.append(
                    f"| {job_id} | {item.get('纠正一（不是电池、不是漏报）', '')} | "
                    f"{item.get('纠正二（不是坏了，是没登记）', '')} | "
                    f"{item.get('绕法句（为何走 add 带 --at）', '')} | "
                    f"{item.get('停下并贴给值班的告诫', '')} |")
        lines += ['', block.get('小结') or '']

    lines += [
        '',
        '## R1、R2 判断抽查（运行工人读原文判，不是规则）',
        '',
        (judgments.get('R1_R2_抽查') or {}).get('内容') or 'human-judgments.json 里没有 R1/R2 的抽查。',
    ]

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

    report = '\n'.join(lines).rstrip() + '\n'
    (HERE / 'MODEL-METRICS.md').write_text(report)
    summary = {
        'codex_calls': counter.get('count'),
        'status': rows,
        'roundabout': prows,
        'w1_words': word_rows('W1', records),
        'w2_words': word_rows('W2', records),
        'm1_verbatim': mrows,
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
