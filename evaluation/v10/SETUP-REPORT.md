# v10 出题记录（worker 报告）

出题工人 2026-11-06 冻结。只出题、写脚本，没有运行 codex，没有改 evaluation/v10 以外的任何文件。

## 交付物

- `prompts.json`：6 题（W1、W2、R1、R2、C1、M1），每题含测的规则、稿子文件、给 Codex 的原话（prompt 栏）、稿子主问题句、必须保留的内容、判卷要看什么、什么算好、什么算错。C1、M1 额外列了陷阱清单。
- `run.py`：改自 v09。CONTROL_REV=a5bfa83，VARIED=('unslop',)，REFUSE_AT=150（limit 200），MODELS 不变（Sol×2 + Astra×1，两组共 36 次计划调用）。单轮、read-only；隔离方式同 v09（每进程空 HOME + 临时 CODEX_HOME，auth 由 run.py 运行时复制，脚本不读内容）；两组都 `install.py --method copy --voice`，对照组再把 unslop 换成 a5bfa83 版本；计数文件独立放在 `evaluation/v10/results/codex-call-count.json`。保留 `--check`（不调用 codex）与 `--pilot`（pilot 用 W1，两组各 Sol 一次）。
- `fixtures/build.py` + `fixtures/src/`：新领域的可运行小项目——温度传感器记录器（`temp_log.py` 记数/统计 CLI + `logger.json` 配置 + `tools/gap_scan.py` 缺口扫描 + smoke tests）。每题一个夹具目录，docs/ 下放冻结稿子，逐题密度断言写进 build.py，不足会直接构建失败。M1 的数据与稿子里的命令、输出、验收数字实跑核对过。
- `FREEZE.sha256`：prompts.json、run.py、fixtures 下全部 8 个文件的指纹，`shasum -a 256 -c` 全部 OK（见下）。

## 测的两条规则

- 规则 41（W1、W2 主测）：生词第一次出现，能换成日常说法的就直接换掉；换不掉的（代号、字段名、命令本身要被提到时）才保留原词并在第一次出现时补一句解释。
- 规则 42（R1、R2 主测）：一句话只说一层转折，先说判断再说依据；对方确实猜错时"不是 A，是 B"的纠正保留。
- C1 陷阱：去绕法不能去掉正确纠正。M1 混合 + 命令、代码、路径、报错原文逐字保留（用 $technical-bro）。

## 每题主问题句（均为稿子原文，计数已实跑核对）

- **W1 进展说明（规则 41）**，主问题句 7 句，英文/自造词 7 种共 11 处：①「nightly 已经跑通，warmup 过滤还没定稿，缺段缝合先不做」②「产出写到 csv_dir 指定的目录……要换成报表专用的目录，改 logger.json 里的这一项就行」（csv_dir 必须保留）③「warmup 过滤针对的是探头刚通电那几分钟」④「outlier 这轮只标不删：周二夜里出现过两个 31.2」⑤「drift 的复测排在下周」⑥「缺段缝合等缺口工具稳定后再排」⑦「写在 logger.json 的 report_hour，下个月改成八点」（report_hour 必须保留）。能换的 5 个：nightly、warmup、outlier、drift、缺段缝合；必须保留的 2 个：csv_dir、report_hour。
- **W2 口径说明（规则 41）**，主问题句 6 句，英文/自造词 8 种共 10 处：①「切天按 localtime，不按 utc」（2 处 utc）②「半小时归一个 bucket……整点对齐还没定稿」（3 处）③「名字对照就写在 logger.json 的 sensors 里」（sensors 必须保留）④「rounding 用四舍五入」⑤「offset 等复测完再写」⑥「维持 report_hour 现在的七点」（report_hour 必须保留）。能换 6 个：localtime、utc、bucket、整点对齐、rounding、offset；必须保留 2 个：sensors、report_hour。
- **R1 方案说明（规则 42）**，"不是 A，而是 B"6 处：①「要解决的不是日报本身难看，而是数据在进门时就没有统一口径」②「清洗不是没做，而是散在两处……同一天能对出两个最低温」③「这不是技术做不到，而是等出日报才发现一夜的数落到了前一天」④「不是因为数据不够，而是没人看这么细」⑤「留空不是因为插值难算，而是编出来的平滑数会骗过最冷时刻的判断」⑥「选的不是最完备的口径，而是出了错最容易发现的那一种」。
- **R2 变更说明（规则 42）**，绕法 5 处（"不是"类标记 6 处，含"既不是……也不是……"1 处）：①「换掉不是因为旧脚本算错过，而是它每次都从头读全部读数」（事实"旧脚本没算错"必须保住）②「既不是格式不合适，也不是没人会改，卡在导入旧数据的脚本还没写」③「它不是又一套汇总口径，而是和日报共用同一段过滤规则」④「这不是为了提前交差，而是给夜里补录留出核对时间」（假想否认要删、理由要留）⑤「不是怕改代码，而是校准值以后大概率还要调……出错时连原始数都找不回来」。
- **C1 排查记录（陷阱：纠正必须保住 + 真绕法要拆）**：必须保住的正确判断①「不是表串列，是录入口把阳台探头 S1 后半夜的数记在了客厅 S2 名下」②「也不是电池的事，是两台探头同一分钟各报一条……配错了行」③定性「这不算缺陷，而是当时赶上线图快」；要拆的真绕法「之所以当场没发现，不是因为日志没打，而是写串的两条时间戳一模一样……而这个场景一直没人想到要查」（三层）。数字 4.6、18.4、六条必须保住。
- **M1 修复指引（混合 + 逐字保留）**：必须逐字保留 11 项——五条命令行、示例输出两行（含制表符）「S1<TAB>2026-11-05<TAB>0,1,2,3,4」「S2<TAB>2026-11-05<TAB>3,4」、报错原文 `unknown sensor id`、代码行 `gaps.setdefault((sensor, day), []).append(str(hour))`、路径 tools/gap_scan.py、data/readings.json、logger.json、配置项 `sensors` 与 `"S3": "书房"`、验收值 count 应为 24；两处正确纠正（「不是电池，也不是 gap_scan 漏报」「这不是坏了，是 S3 还没登记」）必须保住；真绕法「补录之所以走 add 带 --at，不是因为别的办法不行，而是手工改……会弄乱编号」要拆。夹具数据实跑核对：gap_scan 输出两行与稿子一致；登记 S3 后 add 成功；补录两条后 stats 为 count 24、min 18.4、max 22.1、avg 19.9。

## 自检（python3 evaluation/v10/run.py --check，不调用 codex）

```
prompts ok: 6 cases, single-turn, planned calls 36 (refuse at 150)
unslop sha256 control(a5bfa83)=34faf248e5e4… treatment(worktree)=34faf248e5e4… identical=True
W1–M1: arms are identical (worktree unslop still equals the control revision; expected at freeze time)
self-check: the two arms install byte-identical trees. The worktree skills/unslop/SKILL.md still
equals a5bfa83, which is the state at freeze time. After the two rewritten rules land, rerun --check:
it must report that the arms differ only in .agents/skills/unslop/SKILL.md.
setup ok
```

六题 × 两组共 12 次夹具构建 + 安装全通过；arm_diff_files 的"只允许 unslop 不同"判定用构造差异单测过（unslop 不同→只报 unslop；docs 漂移→报出；完全相同→空）。六段 prompt 均不含"说人话/大白话/通俗/别用术语/小白"（run.py --check 里有硬性断言）。

## grep 与冻结校验

- 对本机用户名、本机 home 绝对路径递归 grep，evaluation/v10/ 下无匹配。
- 对上一轮六份稿子的领域词（中文字段与英文代号清单）以及禁用领域词做递归 grep（大小写不敏感，含 v09 用过的英文字段名），evaluation/v10/ 下无匹配；fixture 领域为温度传感器记录器，未复用任何旧题或旧领域。
- `shasum -a 256 -c FREEZE.sha256`：8 行全部 OK。

## 剩下的事（不归这一步）

1. 把改过的两条规则写进 skills/unslop/SKILL.md（协调者负责，对照组仍用 a5bfa83）。
2. 重跑 `python3 evaluation/v10/run.py --check`，应报告两组只有 `.agents/skills/unslop/SKILL.md` 不同；不是这个结果不要开跑。可先 `--pilot`（W1，两组各 Sol 一次，约 2 次调用）。
3. 跑真评测（36 次计划调用，重试上限 150），出盲看页给用户定输赢。
