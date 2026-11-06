#!/usr/bin/env python3
"""Build the v09 case repositories into a caller-supplied directory.

Uses only the Python standard library and git. Sources live in ./src next to
this file. Refuses to write inside the ytstack checkout so a generated tree
cannot get mixed into the freeze.

Every case is the same small expense/queue project plus one frozen draft
document under docs/. The drafts are dense with the four problem types the
new unslop rules will target. The checks below assert each draft keeps its
main problem at least four times, so the freeze cannot silently drift.

The draft world is invented for this fixture. It borrows sentence patterns
from real AI writing, but no project names, amounts, or product names from
that material appear here.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = HERE / 'src'
CASES = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6')

DOC_U1 = """# 两周进展

本周把账本这边的三件事推进到了节点 02：dedupe_key 已经落库，pending_pool 已经接上，month_summary 还差验收。

dedupe_key 这轮走的是 mvp 口径，只认 title 加 cents 完全一致的组合，不上 fuzzy。跑了一轮 backfill，历史 214 条里命中 9 条，全部进了 pending_pool 等人工确认，没有做静默合并。

pending_pool 目前只有只读视图，confirm 流程下周补。视图按 snap 分组展示，编号已经推进到 S-0317，期间没有触发回滚。

month_summary 卡在口径上：按自然月切，还是按滚动 30 天窗口切，两边的数据都跑出来了，等负责人定，定下来之前先不做增量回放。

另外同步一下队列这边：gc_pass 已经上线并接入了定时任务，之后不需要人工介入。
"""

DOC_U2 = """# 去重设计说明

这次要解决的不是重复账本身，而是导入缺少一个统一的判定入口。现状也不是完全没有去重，而是去重散在手工录入和导入两个入口，两边口径不一致。

第一版不做 fuzzy 匹配。这不是因为 fuzzy 没有价值，而是因为它的误报代价高于漏报，而 pending_pool 的人工确认量会因此翻倍。判定顺序先比 title 的精确相等，再比 cents，不是先算相似度再筛金额，因为相似度阈值目前没有校准依据。

评审时有意见认为判定应该挂在导出侧。这不是权限问题，而是时机问题：等导出时才发现重复，账面已经乱了，回头清理的成本远高于在入口拦下。

pending_pool 的定位：它不是一张待办清单，而是"疑似重复、等人工确认"的暂存区，确认权在人。

结论：这一版选的不是最完备的方案，而是失败代价最小的方案，后续再按确认数据迭代。
"""

DOC_U3 = """# v0.4.0 发布说明

本月发布 3 个版本，共 41 个提交，关闭 17 个 issue，其中 P1 有 5 个，回归 2 个，平均修复 2.3 天，上月是 4.1 天。

去重上线第一周拦截 63 笔，误报 4 笔，准确率 93.7%，pending_pool 积压从 214 降到 51，其中确认合并 38、驳回 9、超时放行 4。

性能：导入 5000 条从 8.2 秒降到 3.1 秒，内存峰值从 480MB 降到 210MB，单机 QPS 从 120 提到 310。

队列侧 gc_pass 本周期清理 1247 条，释放 3.2MB，扫描间隔维持 86400 秒。

下个版本做 confirm 流程和导出侧的 export_mask，当前完成度分别是 60% 和 20%，预计 11 月 28 日和 12 月 5 日两次发版带上。
"""

DOC_U4 = """# 三月合计多算 1200 分：记录

上周五对账发现三月合计多了 1200 分。已排查，已定位，已在修。

结论先说：问题出在 void 的写入时机，不是汇总算错。已复核三遍，每次都指向同一处。

当时 add 先写入 12 笔，随后 void 作废其中 2 笔。但它没有当场生效，而是拖到下一次导入才写进去。这就让 summary 在周三夜里到周四早上之间一直读到旧状态。这也是当晚对账差一笔的直接原因。受影响的只有汇总视图，报表和导出不读这份缓存，这可以放心。

已回滚当晚的汇总任务。这没有动原始账，只重建了汇总缓存，耗时 40 秒。已同步值班群。

后续：给 void 补即时写入，这能从根上堵住同类问题，预计本周四上线。另外会加一条对账告警，阈值先定 1 分，它只提示不拦截，误报多了再调。
"""

DOC_U5 = """# 排查记录：导出少三笔

现象：导出的 csv 比列表少 3 笔，少的都是作废后又恢复的账。

我先猜是导出的过滤条件写反了。核对之后：不是过滤条件写反，是恢复操作没有清掉 void_reason，这批账仍带着作废原因，被导出侧跳过。

接着猜是不是 csv 有行数上限。也不是行数上限，是恢复入口只回写了 voided 这一位，void_reason 属于附注字段，不跟着回写。这不算实现缺陷，而是当时为审计留痕有意安排的：留痕要保留"谁在何时作废"，但恢复这条路没人补清空逻辑。之所以恢复时没顺手清掉，不是因为没想到，而是当时判断清空不该由恢复入口做，该由独立对账步骤做，而这个步骤一直没排上。

处理：已写一次性回填脚本，扫全库命中 17 条，跑完复核导出行数。脚本不进主干，跑一次就删。
"""

TAB = '\t'
DOC_U6 = f"""# 修复指引：三月合计多算 36100 分

受影响的是导入过旧备份的账本，当前合计 72700，应为 36600。已确认成因是三月那批重复录入。先跑这一条判断要不要处理：

    python3 tools/dedup_scan.py --state data/ledger.json

输出按「标题{TAB}金额{TAB}编号」分组，一行出现两个以上编号就是中招，例如：

    房租{TAB}24000{TAB}1,5

确认后按编号逐笔作废，一次一条：

    python3 expense_cli.py --state data/ledger.json void 5
    python3 expense_cli.py --state data/ledger.json void 6
    python3 expense_cli.py --state data/ledger.json void 7

编号不存在时会打印 unknown expense id，这时先 list 核对，别猜编号。验收跑 summary：

    python3 expense_cli.py --state data/ledger.json summary

total_cents 应为 36600。不是这个数就停，把上面几条命令的输出原样贴给值班，不要手工改 data/ledger.json。判定逻辑在 tools/dedup_scan.py 里，是这一行：

    groups.setdefault((row['title'], row['cents']), []).append(row['id'])
"""

LEDGER_U6 = [
    {'id': 1, 'title': '房租', 'cents': 24000, 'category': '住', 'voided': False},
    {'id': 2, 'title': '电费', 'cents': 8600, 'category': '住', 'voided': False},
    {'id': 3, 'title': '午饭', 'cents': 3500, 'category': '吃', 'voided': False},
    {'id': 4, 'title': '胶带', 'cents': 500, 'category': '杂项', 'voided': False},
    {'id': 5, 'title': '房租', 'cents': 24000, 'category': '住', 'voided': False},
    {'id': 6, 'title': '电费', 'cents': 8600, 'category': '住', 'voided': False},
    {'id': 7, 'title': '午饭', 'cents': 3500, 'category': '吃', 'voided': False},
]

DOCS = {
    'U1': ('docs/进展说明.md', DOC_U1),
    'U2': ('docs/设计说明.md', DOC_U2),
    'U3': ('docs/发布说明.md', DOC_U3),
    'U4': ('docs/事故记录.md', DOC_U4),
    'U5': ('docs/排查记录.md', DOC_U5),
    'U6': ('docs/修复指引.md', DOC_U6),
}

U1_TERMS = ('dedupe_key', 'pending_pool', 'month_summary', 'fuzzy', 'backfill',
            'snap', 'gc_pass', '静默合并', '增量回放', 'mvp', 'confirm', '节点 02')
EXPLAIN_MARKS = ('也就是', '是指', '指的是', '（指', '（即', '意思是')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith('\n') else text + '\n')


def dump_json(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2))


def nonws(text):
    return len(re.sub(r'\s', '', text))


def git_env(date=None):
    empty = Path(tempfile.gettempdir()) / 'ytstack-v09-empty-gitconfig'
    if not empty.exists():
        empty.write_text('')
    env = os.environ.copy()
    env['GIT_CONFIG_GLOBAL'] = str(empty)
    env['GIT_CONFIG_NOSYSTEM'] = '1'
    env['GIT_AUTHOR_NAME'] = 'Fixture'
    env['GIT_AUTHOR_EMAIL'] = 'fixture@example.invalid'
    env['GIT_COMMITTER_NAME'] = 'Fixture'
    env['GIT_COMMITTER_EMAIL'] = 'fixture@example.invalid'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if date:
        env['GIT_AUTHOR_DATE'] = date
        env['GIT_COMMITTER_DATE'] = date
    return env


def run_git(repo, args, date=None):
    cmd = ['git', '-c', 'core.autocrlf=false', '-c', 'user.name=Fixture',
           '-c', 'user.email=fixture@example.invalid', *args]
    subprocess.run(cmd, cwd=repo, check=True, env=git_env(date),
                   stdout=subprocess.DEVNULL)


def git_text(repo, args):
    result = subprocess.run(
        ['git', '-c', 'core.autocrlf=false', *args], cwd=repo, check=True,
        capture_output=True, text=True, env=git_env())
    return result.stdout


def run_py(repo, args, timeout=20):
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run(
        [sys.executable, *args], cwd=repo, check=False, capture_output=True,
        text=True, timeout=timeout, env=env)


def clean_bytecode(root):
    for path in root.rglob('__pycache__'):
        shutil.rmtree(path)
    for path in root.rglob('*.pyc'):
        path.unlink()


def assert_clean(repo):
    clean_bytecode(repo)
    status = git_text(repo, ['status', '--porcelain'])
    if status.strip():
        raise SystemExit(f'{repo.name} is dirty:\n{status}')


def copy_base(case):
    if case.exists():
        shutil.rmtree(case)
    case.mkdir(parents=True)
    shutil.copy2(SRC / 'queue_cli.py', case / 'queue_cli.py')
    shutil.copy2(SRC / 'expense_cli.py', case / 'expense_cli.py')
    shutil.copy2(SRC / 'README.md', case / 'README.md')
    tests = case / 'tests'
    tests.mkdir()
    shutil.copy2(SRC / 'test_smoke.py', tests / 'test_smoke.py')


def commit_all(repo, message, date):
    clean_bytecode(repo)
    run_git(repo, ['add', '-A'])
    run_git(repo, ['commit', '-q', '-m', message], date=date)


def init_repo(case, message, date):
    run_git(case, ['init', '-q', '-b', 'main'])
    commit_all(case, message, date)


def require_ok(repo, relative):
    result = run_py(repo, [relative])
    if result.returncode != 0:
        raise SystemExit(f'{repo.name} {relative} should pass:\n{result.stdout}\n{result.stderr}')


def check_doc(name, relative, text):
    """Assert the frozen draft keeps its main problem at least four times."""
    total = nonws(text)
    if not 300 <= total <= 600:
        raise SystemExit(f'{name} draft is {total} non-whitespace chars, want 300-600')
    if name == 'U1':
        hits = sum(text.count(term) for term in U1_TERMS)
        distinct = sum(1 for term in U1_TERMS if term in text)
        if hits < 12 or distinct < 8:
            raise SystemExit(f'U1 unexplained-term density drifted: {hits} hits, {distinct} distinct')
        if any(mark in text for mark in EXPLAIN_MARKS):
            raise SystemExit('U1 draft explains a term; that would defuse the question')
    elif name == 'U2':
        if text.count('不是') < 6 or text.count('而是') < 5:
            raise SystemExit(f'U2 contrast density drifted: 不是 {text.count("不是")}, 而是 {text.count("而是")}')
    elif name == 'U3':
        sentences = re.split(r'[。；\n]', text)
        stuffed = [s for s in sentences if len(re.findall(r'\d+(?:\.\d+)?', s)) >= 4]
        if len(stuffed) < 4:
            raise SystemExit(f'U3 number-stuffed sentences drifted: {len(stuffed)}')
    elif name == 'U4':
        starts = (len(re.findall(r'(?:^|[。；，\n])\s*已', text))
                  + len(re.findall(r'[，。；\n]\s*(?:但?它|这)', text)))
        if starts < 10:
            raise SystemExit(f'U4 dropped-subject/unclear-referent clauses drifted: {starts}')
    elif name == 'U5':
        for needle in ('不是过滤条件写反', '也不是行数上限', '不算实现缺陷', '不是因为没想到'):
            if needle not in text:
                raise SystemExit(f'U5 lost trap sentence: {needle}')
        if text.count('不是') < 4 or text.count('而是') < 2:
            raise SystemExit('U5 roundabout density drifted')
    elif name == 'U6':
        keep = [
            'python3 tools/dedup_scan.py --state data/ledger.json',
            'python3 expense_cli.py --state data/ledger.json void 5',
            'python3 expense_cli.py --state data/ledger.json void 6',
            'python3 expense_cli.py --state data/ledger.json void 7',
            'python3 expense_cli.py --state data/ledger.json summary',
            'unknown expense id',
            'total_cents 应为 36600',
            "groups.setdefault((row['title'], row['cents']), []).append(row['id'])",
            f'房租{TAB}24000{TAB}1,5',
        ]
        for needle in keep:
            if needle not in text:
                raise SystemExit(f'U6 lost a verbatim block: {needle!r}')
        starts = re.findall(r'(?:^|[。！？\n])\s*已', text)
        if len(starts) < 1:
            raise SystemExit('U6 prose should still carry some mixed problems')
    print(f'checked {name} {relative}')


def build_case(root, name, extra=None, check=None):
    case = root / name
    copy_base(case)
    relative, text = DOCS[name]
    check_doc(name, relative, text)
    write(case / relative, text)
    if extra:
        extra(case)
    init_repo(case, '放上队列、账本，和一份要改写的稿子。', '2026-11-07T09:00:00+08:00')
    require_ok(case, 'tests/test_smoke.py')
    if check:
        check(case)
    assert_clean(case)


def extra_u6(case):
    tools = case / 'tools'
    tools.mkdir()
    shutil.copy2(SRC / 'dedup_scan.py', tools / 'dedup_scan.py')
    dump_json(case / 'data/ledger.json', LEDGER_U6)


def check_u6(case):
    scan = run_py(case, ['tools/dedup_scan.py', '--state', 'data/ledger.json'])
    if scan.returncode != 0:
        raise SystemExit(f'U6 dedup_scan failed:\n{scan.stderr}')
    expected = f'午饭{TAB}3500{TAB}3,7\n房租{TAB}24000{TAB}1,5\n电费{TAB}8600{TAB}2,6\n'
    if scan.stdout != expected:
        raise SystemExit(f'U6 dedup_scan output drifted:\n{scan.stdout!r}\nwant\n{expected!r}')
    original = (case / 'data/ledger.json').read_text()
    with tempfile.TemporaryDirectory() as directory:
        state = Path(directory) / 'ledger.json'
        state.write_text(original)
        for row_id in (5, 6, 7):
            voided = run_py(case, ['expense_cli.py', '--state', str(state), 'void', str(row_id)])
            if voided.returncode != 0:
                raise SystemExit(f'U6 void {row_id} failed:\n{voided.stderr}')
        summary = run_py(case, ['expense_cli.py', '--state', str(state), 'summary'])
        parsed = json.loads(summary.stdout)
        if summary.returncode != 0 or parsed['total_cents'] != 36600 or parsed['count'] != 4:
            raise SystemExit(f'U6 fixed total drifted: {summary.stdout}')
    if (case / 'data/ledger.json').read_text() != original:
        raise SystemExit('U6 check modified the fixture ledger')


def build_u1(root):
    build_case(root, 'U1')


def build_u2(root):
    build_case(root, 'U2')


def build_u3(root):
    build_case(root, 'U3')


def build_u4(root):
    build_case(root, 'U4')


def build_u5(root):
    build_case(root, 'U5')


def build_u6(root):
    build_case(root, 'U6', extra=extra_u6, check=check_u6)


def build(root):
    root.mkdir(parents=True, exist_ok=True)
    for name in CASES:
        extra = extra_u6 if name == 'U6' else None
        check = check_u6 if name == 'U6' else None
        build_case(root, name, extra=extra, check=check)
        print(f'built {name}')


def main():
    parser = argparse.ArgumentParser(description='Build v09 fixtures into OUTPUT.')
    parser.add_argument('output', type=Path, help='directory to create; case folders are written inside it')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == REPO or REPO in output.parents:
        raise SystemExit(f'refusing to write inside the ytstack repo: {output}')
    sources = (
        SRC / 'queue_cli.py', SRC / 'expense_cli.py', SRC / 'test_smoke.py',
        SRC / 'README.md', SRC / 'dedup_scan.py',
    )
    for source in sources:
        if not source.is_file():
            raise SystemExit(f'missing source file: {source}')
    build(output)
    print(f'ok {output}')


if __name__ == '__main__':
    main()
