#!/usr/bin/env python3
"""Build the v10 case repositories into a caller-supplied directory.

Uses only the Python standard library and git. Sources live in ./src next to
this file. Refuses to write inside the ytstack checkout so a generated tree
cannot get mixed into the freeze.

Every case is the same small temperature-logger project plus one frozen draft
document under docs/. The drafts are dense with the two problem types the
rewritten unslop rules target (rule 41: replace borrowed words with everyday
wording unless the word itself is the thing under discussion; rule 42: one
turn per sentence, judgment before reason, keep genuine "no, it's B"
corrections). The checks below assert each draft keeps its main problem at
the density the freeze promises, so the freeze cannot silently drift.

The draft world is invented for this fixture. It borrows sentence patterns
from real AI writing, but nothing from earlier evaluation rounds is reused
here.
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
CASES = ('W1', 'W2', 'R1', 'R2', 'C1', 'M1')

DOC_W1 = """# 两周进展

温度记录这边的三件事都有新进展：nightly 已经跑通，warmup 过滤还没定稿，缺段缝合先不做。

nightly 目前每晚十一点跑一次，产出写到 csv_dir 指定的目录，第二天早上负责人直接看前一晚的数。csv_dir 现在指向 out，要换成报表专用的目录，改 logger.json 里的这一项就行。

warmup 过滤针对的是探头刚通电那几分钟：读数会飘。这版先不做，等攒够对比数据再定。

outlier 这轮只标不删：周二夜里出现过两个 31.2，明显偏离前后读数，先挂在名单里等人工看。

drift 的复测排在下周：阳台探头连续两周偏高约 0.4，怀疑日晒影响，挪位置后再对比一周。

日报的钟点定在七点，写在 logger.json 的 report_hour，下个月改成八点，请负责人顺手改掉这一项。缺段缝合等缺口工具稳定后再排。
"""

DOC_W2 = """# 数据口径说明

这份定温度数据进库时的几条口径，请负责人过目后回个话。

切天按 localtime，不按 utc：读数的时间本来就是本地钟点，按 utc 切会把凌晨两点到八点的数算进前一天。

半小时归一个 bucket：原始读数一分钟一条，直接画图太密，归组后够看趋势。bucket 边界的整点对齐还没定稿。

传感器改名只改显示名，不改编号：旧记录里存的是 S1、S2，直接改编号会对不上历史。名字对照就写在 logger.json 的 sensors 里，要加新探头时往这一项里补一行，别动别的。

小数位统一留一位，rounding 用四舍五入：原来有的留一位有的留两位，报表对不齐。

校准值先不进库：offset 等复测完再写，现在写进去以后改起来麻烦。日报钟点维持 report_hour 现在的七点，这个值先不要动。
"""

DOC_R1 = """# 日报改版方案

这次要解决的不是日报本身难看，而是数据在进门时就没有统一口径，后面怎么排版都补不回来。

清洗不是没做，而是散在两处：记数时滤一遍，出日报时又滤一遍，两边规则不一致，同一天能对出两个最低温，这样的事上个月出过三回。

凌晨切天不放到导出时做。这不是技术做不到，而是等出日报才发现一夜的数落到了前一天，回头补的手工量翻倍。

日报不做分钟级曲线，不是因为数据不够，而是没人看这么细，画出来反而把真正的跳变淹掉。真要看细节，日表底下还挂着半小时一格的原始数。

缺段先留空，不插值。留空不是因为插值难算，而是编出来的平滑数会骗过最冷时刻的判断，宁可空着让人一眼看出断在哪里。

结论：这一版选的不是最完备的口径，而是出了错最容易发现的那一种，后面再按实际情况收紧。
"""

DOC_R2 = """# 变更说明：日报脚本换掉

这版把每天算最低最高的脚本换掉了。换掉不是因为旧脚本算错过，而是它每次都从头读全部读数，数据一多就跑不动，早晨的日报经常迟半个钟头。

改版前讨论过换存储格式。既不是格式不合适，也不是没人会改，卡在导入旧数据的脚本还没写，换过去等于把一个月的读数锁在旧文件里。

新脚本只扫当天的数。它不是又一套汇总口径，而是和日报共用同一段过滤规则，算完直接进日报，不再单独存一份。

汇总钟点从七点挪到六点半。这不是为了提前交差，而是给夜里补录留出核对时间，请值班的人注意时间变了。

下一版加校准。校准不在记数时做，不是怕改代码，而是校准值以后大概率还要调，写进每条读数就固化了，出错时连原始数都找不回来。
"""

DOC_C1 = """# 排查记录：五日客厅最低温 4.6

日报上五日客厅最低温 4.6，室内探头不可能这么低。负责人先猜是探头坏了。

我先猜导出的表串了列。核对后：不是表串列，是录入口把阳台探头 S1 后半夜的数记在了客厅 S2 名下，室内那行混进了室外数，最低温就被拉到了 4.6。

接着猜是不是电池电压低，数飘了。也不是电池的事，是两台探头同一分钟各报一条，录入口按到达先后配编号，配错了行。这不算缺陷，而是当时赶上线图快，登记表没接进录入口，这个口子后来一直没人补。

之所以当场没发现，不是因为日志没打，而是写串的两条时间戳一模一样，排序后紧挨着，看着就像正常的连续读数，而这个场景一直没人想到要查。

处理：写串的六条改回原探头，客厅五日最低温重算为 18.4。录入口接上登记表，编号对不上直接拒收。改数只此一次，之后一律先查日志再动手。
"""

TAB = '\t'
DOC_M1 = f"""# 修复指引：五日客厅缺两条

五日客厅的日报缺了两条。值班先猜电池没电，又猜工具漏报。核对后：不是电池，也不是 gap_scan 漏报，是探头重启时丢了两条。先跑这一条看缺口：

    python3 tools/gap_scan.py --state data/readings.json

输出按「探头{TAB}日期{TAB}缺的钟点」列，五日应有两行：

    S1{TAB}2026-11-05{TAB}0,1,2,3,4
    S2{TAB}2026-11-05{TAB}3,4

S1 那行正常：阳台探头只在白天通电，夜里本来就没数。S2 缺的 3、4 点要补。补录之所以走 add 带 --at，不是因为别的办法不行，而是手工改 data/readings.json 会弄乱编号，出错没处查：

    python3 temp_log.py --state data/readings.json add S2 18.5 --at 2026-11-05T03:00
    python3 temp_log.py --state data/readings.json add S2 18.5 --at 2026-11-05T04:00

补完验收跑 stats：

    python3 temp_log.py --state data/readings.json stats --sensor S2

count 应为 24。不是这个数就停，把三条命令的输出原样贴给值班。

新探头直接记数会被拒，这条会打印 unknown sensor id：

    python3 temp_log.py --state data/readings.json add S3 21.8

这不是坏了，是 S3 还没登记：把 "S3": "书房" 补进 logger.json 的 sensors 里，再重跑上面那条。缺口的判定在 tools/gap_scan.py，是这一行：

    gaps.setdefault((sensor, day), []).append(str(hour))
"""

DOCS = {
    'W1': ('docs/进展说明.md', DOC_W1),
    'W2': ('docs/口径说明.md', DOC_W2),
    'R1': ('docs/方案说明.md', DOC_R1),
    'R2': ('docs/变更说明.md', DOC_R2),
    'C1': ('docs/排查记录.md', DOC_C1),
    'M1': ('docs/修复指引.md', DOC_M1),
}

# 阳台探头 S1 只在白天通电（05-23 点）；客厅探头 S2 缺 3、4 点（探头重启）。
S1_DAY = [
    (5, 15.8), (6, 15.6), (7, 16.2), (8, 17.5), (9, 18.9), (10, 20.1),
    (11, 21.0), (12, 21.4), (13, 21.2), (14, 20.8), (15, 20.3), (16, 19.4),
    (17, 18.2), (18, 17.1), (19, 16.5), (20, 16.0), (21, 15.7), (22, 15.5), (23, 15.4),
]
S2_DAY = [
    (0, 18.5), (1, 18.4), (2, 18.6), (5, 19.0), (6, 19.1), (7, 19.0), (8, 19.2),
    (9, 19.5), (10, 20.0), (11, 20.6), (12, 21.3), (13, 21.8), (14, 22.0), (15, 22.1),
    (16, 22.0), (17, 21.6), (18, 21.0), (19, 20.4), (20, 19.8), (21, 19.4), (22, 19.1), (23, 18.9),
]

W1_TERMS = ('nightly', 'warmup', '缺段缝合', 'csv_dir', 'report_hour', 'outlier', 'drift')
W2_TERMS = ('localtime', 'utc', 'bucket', '整点对齐', 'sensors', 'rounding', 'offset', 'report_hour')
EXPLAIN_MARKS = ('也就是', '是指', '指的是', '（指', '（即', '意思是')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith('\n') else text + '\n')


def nonws(text):
    return len(re.sub(r'\s', '', text))


def git_env(date=None):
    empty = Path(tempfile.gettempdir()) / 'ytstack-v10-empty-gitconfig'
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
    shutil.copy2(SRC / 'temp_log.py', case / 'temp_log.py')
    shutil.copy2(SRC / 'logger.json', case / 'logger.json')
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
    """Assert the frozen draft keeps the problem density the freeze promises."""
    total = nonws(text)
    top = 800 if name == 'M1' else 600  # M1 carries five command lines plus code and output blocks.
    if not 300 <= total <= top:
        raise SystemExit(f'{name} draft is {total} non-whitespace chars, want 300-{top}')
    if name in ('W1', 'W2'):
        terms = W1_TERMS if name == 'W1' else W2_TERMS
        hits = sum(text.count(term) for term in terms)
        distinct = sum(1 for term in terms if term in text)
        if hits < 10 or distinct < len(terms):
            raise SystemExit(f'{name} borrowed-word density drifted: {hits} hits, {distinct} distinct')
        if any(mark in text for mark in EXPLAIN_MARKS):
            raise SystemExit(f'{name} draft explains a term; that would defuse the question')
    elif name in ('R1', 'R2'):
        if text.count('不是') < 5 or text.count('而是') < 3:
            raise SystemExit(
                f'{name} contrast density drifted: 不是 {text.count("不是")}, 而是 {text.count("而是")}')
        if '猜' in text:
            raise SystemExit(f'{name} carries a guessed-then-corrected shape; that belongs to C1')
        if name == 'R2' and '既不是' not in text:
            raise SystemExit('R2 lost the 既不是……也不是…… pattern')
    elif name == 'C1':
        for needle in ('不是表串列', '也不是电池的事', '不算缺陷', '之所以当场没发现', '不是因为日志没打'):
            if needle not in text:
                raise SystemExit(f'C1 lost trap sentence: {needle}')
        for fact in ('4.6', '18.4', '六条'):
            if fact not in text:
                raise SystemExit(f'C1 lost a fact that must survive: {fact}')
    elif name == 'M1':
        keep = [
            'python3 tools/gap_scan.py --state data/readings.json',
            'python3 temp_log.py --state data/readings.json add S2 18.5 --at 2026-11-05T03:00',
            'python3 temp_log.py --state data/readings.json add S2 18.5 --at 2026-11-05T04:00',
            'python3 temp_log.py --state data/readings.json stats --sensor S2',
            'python3 temp_log.py --state data/readings.json add S3 21.8',
            'unknown sensor id',
            'count 应为 24',
            '"S3": "书房" 补进 logger.json 的 sensors',
            'gaps.setdefault((sensor, day), []).append(str(hour))',
            f'S1{TAB}2026-11-05{TAB}0,1,2,3,4',
            f'S2{TAB}2026-11-05{TAB}3,4',
        ]
        for needle in keep:
            if needle not in text:
                raise SystemExit(f'M1 lost a verbatim block: {needle!r}')
        for pattern in ('不是电池', '之所以走 add', '这不是坏了，是 S3 还没登记'):
            if pattern not in text:
                raise SystemExit(f'M1 lost a mixed-problem sentence: {pattern!r}')
    print(f'checked {name} {relative} ({total} chars)')


def build_case(root, name, extra=None, check=None):
    case = root / name
    copy_base(case)
    relative, text = DOCS[name]
    check_doc(name, relative, text)
    write(case / relative, text)
    if extra:
        extra(case)
    init_repo(case, '放上温度记录工具，和一份要改写的稿子。', '2026-11-06T09:00:00+08:00')
    require_ok(case, 'tests/test_smoke.py')
    if check:
        check(case)
    assert_clean(case)


def readings_rows():
    rows = []

    def put(sensor, day, hour, temp):
        rows.append({'id': len(rows) + 1, 'sensor': sensor, 'temp_c': temp,
                     'at': f'{day}T{hour:02d}:00'})

    for hour, temp in S1_DAY:
        put('S1', '2026-11-05', hour, temp)
    for hour, temp in S2_DAY:
        put('S2', '2026-11-05', hour, temp)
    return rows


def extra_m1(case):
    tools = case / 'tools'
    tools.mkdir()
    shutil.copy2(SRC / 'gap_scan.py', tools / 'gap_scan.py')
    write(case / 'data/readings.json',
          json.dumps(readings_rows(), ensure_ascii=False, indent=2))


def check_m1(case):
    scan = run_py(case, ['tools/gap_scan.py', '--state', 'data/readings.json'])
    if scan.returncode != 0:
        raise SystemExit(f'M1 gap_scan failed:\n{scan.stderr}')
    expected = f'S1{TAB}2026-11-05{TAB}0,1,2,3,4\nS2{TAB}2026-11-05{TAB}3,4\n'
    if scan.stdout != expected:
        raise SystemExit(f'M1 gap_scan output drifted:\n{scan.stdout!r}\nwant\n{expected!r}')
    readings_before = (case / 'data/readings.json').read_text()
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / 'proj'
        shutil.copytree(case, copy, ignore=shutil.ignore_patterns('.git'))
        denied = run_py(copy, ['temp_log.py', '--state', 'data/readings.json', 'add', 'S3', '21.8'])
        if denied.returncode != 1 or 'unknown sensor id' not in denied.stderr:
            raise SystemExit(f'M1 unregistered add should fail:\n{denied.stderr}')
        config_path = copy / 'logger.json'
        config = json.loads(config_path.read_text())
        config['sensors']['S3'] = '书房'
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
        for stamp in ('2026-11-05T03:00', '2026-11-05T04:00'):
            filled = run_py(copy, ['temp_log.py', '--state', 'data/readings.json',
                                   'add', 'S2', '18.5', '--at', stamp])
            if filled.returncode != 0:
                raise SystemExit(f'M1 add --at {stamp} failed:\n{filled.stderr}')
        registered = run_py(copy, ['temp_log.py', '--state', 'data/readings.json',
                                   'add', 'S3', '21.8'])
        if registered.returncode != 0:
            raise SystemExit(f'M1 registered add failed:\n{registered.stderr}')
        summary = run_py(copy, ['temp_log.py', '--state', 'data/readings.json',
                                'stats', '--sensor', 'S2'])
        if summary.returncode != 0:
            raise SystemExit(f'M1 stats failed:\n{summary.stderr}')
        parsed = json.loads(summary.stdout)
        if parsed != {'sensor': 'S2', 'count': 24, 'min_c': 18.4, 'max_c': 22.1, 'avg_c': 19.9}:
            raise SystemExit(f'M1 fixed stats drifted: {summary.stdout}')
    if (case / 'data/readings.json').read_text() != readings_before:
        raise SystemExit('M1 check modified the fixture readings')


def build_w1(root):
    build_case(root, 'W1')


def build_w2(root):
    build_case(root, 'W2')


def build_r1(root):
    build_case(root, 'R1')


def build_r2(root):
    build_case(root, 'R2')


def build_c1(root):
    build_case(root, 'C1')


def build_m1(root):
    build_case(root, 'M1', extra=extra_m1, check=check_m1)


def build(root):
    root.mkdir(parents=True, exist_ok=True)
    for name in CASES:
        extra = extra_m1 if name == 'M1' else None
        check = check_m1 if name == 'M1' else None
        build_case(root, name, extra=extra, check=check)
        print(f'built {name}')


def main():
    parser = argparse.ArgumentParser(description='Build v10 fixtures into OUTPUT.')
    parser.add_argument('output', type=Path, help='directory to create; case folders are written inside it')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == REPO or REPO in output.parents:
        raise SystemExit(f'refusing to write inside the ytstack repo: {output}')
    sources = (
        SRC / 'temp_log.py', SRC / 'gap_scan.py', SRC / 'logger.json',
        SRC / 'test_smoke.py', SRC / 'README.md',
    )
    for source in sources:
        if not source.is_file():
            raise SystemExit(f'missing source file: {source}')
    build(output)
    print(f'ok {output}')


if __name__ == '__main__':
    main()
