# v09 模型指标

这些数字只作参考，用户盲看说了算。规则能判的用规则判；需要读意思的（U5 的判断、U1/U4 的观察）是运行工人读原文判的，写在 human-judgments.json，没有调用 Codex 当评委。

Codex 调用次数：36（到 190 拒绝再调用，上限 200）。36 个计划任务全部一次成功，没有用掉重试。

## 隔离和技能版本

每个 codex 子进程使用单独的空 HOME 和单独的 CODEX_HOME。HOME 下没有 .agents。CODEX_HOME 只有复制过来的登录文件和一份最小配置，没有 skills 目录。shell_environment_policy.exclude 含 CODEX_HOME，子进程的 shell 看不到这份目录。没有读取登录文件的内容，也没有改 ~/.agents 或 ~/.codex。

没有加载本机 ~/.codex/config.toml。子进程配置只写了模型、high reasoning、pragmatic、approval_policy=never、sandbox_mode=read-only，以及排除 CODEX_HOME。每题另传 --sandbox read-only。

U1-astra-control-r1 的 skills_read 读了项目里的 unslop，命令路径不是全局 ~/.agents/skills，unslop 的 SKILL.md sha256 等于提交 a5bfa83。

| 技能 | 对照组 sha256（a5bfa83） | 实验组 sha256（工作区） | 不同 |
| --- | --- | --- | --- |
| unslop | `34faf248e5e4d72f877c7ed3f48fedf42dfcd64a93375c7ba9752e28be4c13ff` | `f2a318d4403af7cd0c28cc9d4787be8b4f23a222996cc6ce4c486e50628c7497` | 是 |

两组装出的技能目录只差 .agents/skills/unslop/SKILL.md：是（--check 逐题核过）。

## 运行状态

| 运行 | 状态 | 用时（秒） | 字数 | 读了 unslop |
| --- | --- | ---: | ---: | --- |
| U1-sol-control-r1 | ok | 48.7 | 478 | 读了 |
| U1-sol-control-r2 | ok | 61.6 | 450 | 读了 |
| U1-astra-control-r1 | ok | 60.9 | 479 | 读了 |
| U1-sol-treatment-r1 | ok | 51.2 | 506 | 读了 |
| U1-sol-treatment-r2 | ok | 60.9 | 494 | 读了 |
| U1-astra-treatment-r1 | ok | 59.5 | 488 | 读了 |
| U2-sol-control-r1 | ok | 59.7 | 372 | 读了 |
| U2-sol-control-r2 | ok | 53.7 | 399 | 读了 |
| U2-astra-control-r1 | ok | 55.7 | 389 | 读了 |
| U2-sol-treatment-r1 | ok | 63.4 | 427 | 读了 |
| U2-sol-treatment-r2 | ok | 62.8 | 391 | 读了 |
| U2-astra-treatment-r1 | ok | 46.2 | 376 | 读了 |
| U3-sol-control-r1 | ok | 54.1 | 505 | 读了 |
| U3-sol-control-r2 | ok | 54.1 | 502 | 读了 |
| U3-astra-control-r1 | ok | 47.8 | 563 | 读了 |
| U3-sol-treatment-r1 | ok | 72.4 | 722 | 读了 |
| U3-sol-treatment-r2 | ok | 87.6 | 711 | 读了 |
| U3-astra-treatment-r1 | ok | 61.9 | 708 | 读了 |
| U4-sol-control-r1 | ok | 65.4 | 355 | 读了 |
| U4-sol-control-r2 | ok | 48.3 | 377 | 读了 |
| U4-astra-control-r1 | ok | 54.6 | 426 | 读了 |
| U4-sol-treatment-r1 | ok | 68.1 | 431 | 读了 |
| U4-sol-treatment-r2 | ok | 63.9 | 490 | 读了 |
| U4-astra-treatment-r1 | ok | 56.5 | 422 | 读了 |
| U5-sol-control-r1 | ok | 58.5 | 392 | 读了 |
| U5-sol-control-r2 | ok | 56.1 | 368 | 读了 |
| U5-astra-control-r1 | ok | 45.1 | 384 | 没读 |
| U5-sol-treatment-r1 | ok | 56.3 | 366 | 读了 |
| U5-sol-treatment-r2 | ok | 56.2 | 367 | 读了 |
| U5-astra-treatment-r1 | ok | 49.5 | 370 | 读了 |
| U6-sol-control-r1 | ok | 63.6 | 1139 | 读了 |
| U6-sol-control-r2 | ok | 68.2 | 1237 | 读了 |
| U6-astra-control-r1 | ok | 61.0 | 1152 | 读了 |
| U6-sol-treatment-r1 | ok | 64.1 | 1013 | 读了 |
| U6-sol-treatment-r2 | ok | 63.4 | 1153 | 读了 |
| U6-astra-treatment-r1 | ok | 59.4 | 1006 | 读了 |

状态合计：ok 36。
reads：36 份里 35 份读了 unslop，唯一没读的是 U5-astra-control-r1（对照组，只读了 technical-bro，回复仍然完成了改写）。所有运行读的都是项目里的副本，没有读全局 ~/.agents/skills。

## 绕法计数（规则二表层，规则判）

规则数的是「不是……而是……」和「既不是……也……」两种表层式子（同句内匹配，跨句不算）。

| 运行 | 剩几处 | 原句（截断） |
| --- | ---: | --- |
| U1-sol-control-r1 | 0 |  |
| U1-sol-control-r2 | 0 |  |
| U1-astra-control-r1 | 0 |  |
| U1-sol-treatment-r1 | 0 |  |
| U1-sol-treatment-r2 | 0 |  |
| U1-astra-treatment-r1 | 0 |  |
| U2-sol-control-r1 | 0 |  |
| U2-sol-control-r2 | 0 |  |
| U2-astra-control-r1 | 0 |  |
| U2-sol-treatment-r1 | 0 |  |
| U2-sol-treatment-r2 | 0 |  |
| U2-astra-treatment-r1 | 0 |  |
| U3-sol-control-r1 | 0 |  |
| U3-sol-control-r2 | 0 |  |
| U3-astra-control-r1 | 0 |  |
| U3-sol-treatment-r1 | 0 |  |
| U3-sol-treatment-r2 | 0 |  |
| U3-astra-treatment-r1 | 0 |  |
| U4-sol-control-r1 | 0 |  |
| U4-sol-control-r2 | 0 |  |
| U4-astra-control-r1 | 0 |  |
| U4-sol-treatment-r1 | 0 |  |
| U4-sol-treatment-r2 | 0 |  |
| U4-astra-treatment-r1 | 0 |  |
| U5-sol-control-r1 | 0 |  |
| U5-sol-control-r2 | 0 |  |
| U5-astra-control-r1 | 0 |  |
| U5-sol-treatment-r1 | 0 |  |
| U5-sol-treatment-r2 | 0 |  |
| U5-astra-treatment-r1 | 0 |  |
| U6-sol-control-r1 | 0 |  |
| U6-sol-control-r2 | 0 |  |
| U6-astra-control-r1 | 0 |  |
| U6-sol-treatment-r1 | 0 |  |
| U6-sol-treatment-r2 | 0 |  |
| U6-astra-treatment-r1 | 0 |  |

36 份回复两种式子都是 0 处：两组在这个表层指标上打平，都清干净了。回复里剩下的零星「不是」是条件句（比如「如果 total_cents 不是 36600」），不是绕法。真正的差别藏在 U5 的定性保没保住、U4 的主语补没补、U6 的逐字保留，见下面几节。

## U6 逐字保留（规则判，逐条）

清单就是 prompts.json 里「陷阱（必须原样保留）」的条目，空格和制表符也算。

| 运行 | 命令 1 | 命令 2 | 命令 3 | 命令 4 | 命令 5 | 示例输出行 | 报错原文 | 代码行 | 路径 | 路径 | total_cent | 数字 | 数字 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U6-sol-control-r1 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 |
| U6-sol-control-r2 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 |
| U6-astra-control-r1 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 | 缺 | 缺 | 缺 |
| U6-sol-treatment-r1 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 |
| U6-sol-treatment-r2 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 |
| U6-astra-treatment-r1 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 | 缺 | 逐字 | 逐字 |

逐条结论：

- 五条命令行、示例输出行（制表符原样）、报错原文 unknown expense id、两个路径：六份（两组各三份）全部逐字保留。
- 「total_cents 应为 36600」：六份都没有逐字保留，都改写成了反引号形式（如 `total_cents` 为 `36600`）。数值 36600 都在，丢的只是「应为」这两个字的连写。两组同样如此。
- 代码行 groups.setdefault(...)：六份都整段删掉了（没有一份重排或改写，是不再出现）。原稿最后一段「判定逻辑在 tools/dedup_scan.py 里，是这一行：……」两组都没有保留。这是全组统一的失分点，不区分两组。
- 数字 72700 和 36100：只有 U6-astra-control-r1 两个都丢了（整段改写时把「受影响账本当前合计、多算了多少」的对照句删了），其余五份两个数都在。

## U5 陷阱判断（运行工人读原文判，不是规则）

三个必须保住的判断：一，猜测一（导出过滤条件写反）被明确否定，真原因（恢复没清 void_reason、被导出侧跳过）被明确肯定；二，猜测二（csv 行数上限）被明确否定，真原因（恢复只回写 voided 这一位）被明确肯定；三，「不算实现缺陷、当时为审计留痕有意安排」的定性还在，且不能反过来写成缺陷。

| 运行 | 否定猜测一、肯定真因 | 否定猜测二、肯定真因 | 「有意设计不算缺陷」定性 |
| --- | --- | --- | --- |
| U5-sol-control-r1 | 保住（「排查已排除过滤条件写反和 CSV 行数上限这两个原因」+ 原因段） | 保住（「恢复账目时，程序只把 voided 改回未作废，没有清空作废原因 void_reason」） | 丢了一半：保留了「为保留审计记录决定恢复时保留 void_reason」的设计意图，但删掉了「不算实现缺陷」的明确定性 |
| U5-sol-control-r2 | 保住（「排查已排除导出过滤条件写反和 CSV 行数上限这两个原因」） | 保住（「恢复操作只把 voided 改为未作废，没有清空作废原因 void_reason」） | 丢了一半：意图在（「当时为了保留……的记录，团队决定由独立的对账步骤清空」），明确定性「不算实现缺陷」没有了 |
| U5-astra-control-r1 | 保住（「核对后，已排除导出过滤条件写反和 CSV 行数上限这两个原因」） | 保住（「恢复时，系统只更新了作废状态 voided，没有清空作废原因 void_reason」） | 丢了一半：意图在（「当时为了保留『谁在何时作废』的审计记录」），明确定性没有了 |
| U5-sol-treatment-r1 | 保住（「排查已排除过滤条件写反和 csv 行数上限这两个原因」） | 保住（「恢复操作只更新了 voided……void_reason 属于附注字段，恢复时不会一起更新」），还顺带解释了两个代号 | 保住（「保留作废信息是当时……作出的安排，不算实现缺陷」） |
| U5-sol-treatment-r2 | 保住，且拆得更直（「导出的过滤条件没有写反，csv 也没有行数上限」） | 保住（「恢复操作只更新了 voided……void_reason 是附注字段，恢复时不会跟着更新」） | 保住（「按当时的设计不算实现缺陷」） |
| U5-astra-treatment-r1 | 保住（「排查已排除过滤条件写反和 csv 行数上限这两个原因」） | 保住（「恢复操作只更新表示是否作废的 voided 字段，不更新作为附注保存的 void_reason」） | 保住（「恢复时保留作废原因符合当时的安排，不算实现缺陷」） |

六个否定猜测、肯定真因的判断全部保住。差别在第三个定性：实验组 3 份都保留了「不算实现缺陷」的明确定性；对照组 3 份都只留下设计意图、丢了明确定性。三层转折那句两组都拆开了。

## 字数（两组）

按 Python 字符数数整段回复。

| 组 | 每份字数 | 平均 |
| --- | --- | ---: |
| control | 478，450，479，372，399，389，505，502，563，355，377，426，392，368，384，1139，1237，1152 | 554 |
| treatment | 506，494，488，427，391，376，722，711，708，431，490，422，366，367，370，1013，1153，1006 | 580 |

## 补充：U4 表层计数（规则判，正则）

数的是句首「已……」和无主语指引的「它/这」分句。只看表层，语义上补得对不对见 human-judgments.json。

| 运行 | 句首「已」 | 「它/这」分句 |
| --- | ---: | ---: |
| U4-sol-control-r1 | 2 | 0 |
| U4-sol-control-r2 | 1 | 0 |
| U4-astra-control-r1 | 1 | 0 |
| U4-sol-treatment-r1 | 0 | 0 |
| U4-sol-treatment-r2 | 0 | 0 |
| U4-astra-treatment-r1 | 0 | 0 |

对照组 3 份各留 1–2 句无主语「已……」（已复核三次、已回滚/已撤销当晚汇总任务），实验组 3 份一句不剩，全部补了主语。指代不明的「它/这」开头两组都是 0。

## 补充：U1 观察（运行工人读原文判）

dedupe_key、pending_pool、month_summary 三个主代号两组都解释了（对照组多用同位语「待确认列表」，实验组多用括号「（待人工确认的列表）」）。snap 一词六份里只有 U1-astra-control-r1 一份给出了解释（「数据快照 snap」），其余五份两组都原样保留没解释；S-0317 六份都没解释。gc_pass 两组都只给了「队列任务」这一类标签。事实与数字（214、9、S-0317）六份都全。
