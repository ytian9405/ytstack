# v09 出题记录（worker 报告）

出题工人 2026-11-07 冻结。只出题、写脚本，没有运行 codex，没有改 evaluation/v09 以外的任何文件。

## 交付物

- `prompts.json`：6 题（U1–U6），每题含测的规则、稿子文件、给 Codex 的原话（prompt 栏）、稿子主问题句、判卷要看什么、什么算好、什么算错。U5、U6 额外列了陷阱清单。
- `run.py`：改自 v08。CONTROL_REV=a5bfa83，VARIED=('unslop',)，REFUSE_AT=190（limit 200），MODELS 不变（Sol×2 + Astra×1，两组共 36 次计划调用）。单轮、read-only；隔离方式同 v08（每进程空 HOME + 临时 CODEX_HOME，auth 由 run.py 运行时复制，脚本不读内容）；两组都 `install.py --method copy --voice`，对照组再把 unslop 换成 a5bfa83 版本；去掉 v08 的交接、后台任务、ketchup、triggers、resume 部分。`--check` 自检不调用 codex。
- `fixtures/build.py` + `fixtures/src/`：复用 v08 的 expense/queue 小工具，新增 `dedup_scan.py`；每题一个夹具目录，docs/ 下放冻结稿子。逐题密度断言写进 build.py（主问题不足 4 处会直接构建失败）。
- `FREEZE.sha256`：prompts.json、run.py、fixtures 下全部 7 个文件的指纹，`shasum -a 256 -c` 全部 OK（见下）。

## 每题主问题句（均为稿子原文）

- **U1 进展说明（规则一：英文词、代号、自造词第一次出现要解释）**，未解释词出现 12 个：①「推进到了节点 02：dedupe_key 已经落库，pending_pool 已经接上，month_summary 还差验收」②「走的是 mvp 口径……不上 fuzzy」③「跑了一轮 backfill……没有做静默合并」④「视图按 snap 分组展示，编号已经推进到 S-0317」⑤「先不做增量回放」⑥「gc_pass 已经上线并接入了定时任务」。
- **U2 设计说明（规则二：不叠转折、不用"不是 A，而是 B"）**，7 处：①「要解决的不是重复账本身，而是导入缺少一个统一的判定入口」②「现状也不是完全没有去重，而是去重散在……两个入口」③「这不是因为 fuzzy 没有价值，而是因为它的误报代价高于漏报」④「不是先算相似度再筛金额」⑤「这不是权限问题，而是时机问题」⑥「它不是一张待办清单，而是……暂存区」⑦「选的不是最完备的方案，而是失败代价最小的方案」。
- **U3 发布说明（规则三：一句不塞多个数、数字要带口径）**，5 处：①「3 个版本，共 41 个提交，关闭 17 个 issue，其中 P1 有 5 个，回归 2 个，平均修复 2.3 天，上月是 4.1 天」②「拦截 63 笔，误报 4 笔，准确率 93.7%，积压从 214 降到 51……38、9、4」③「8.2 秒降到 3.1 秒，480MB 降到 210MB，QPS 从 120 提到 310」④「清理 1247 条，释放 3.2MB，扫描间隔维持 86400 秒」⑤「完成度分别是 60% 和 20%，预计 11 月 28 日和 12 月 5 日」。
- **U4 事故记录（规则四：不省主语、不用指代不明的"它/这/已…"）**，10 处：①「已排查，已定位，已在修」②「已复核三遍」③「但它没有当场生效」④「这就让 summary……读到旧状态」⑤「这也是当晚对账差一笔的直接原因」⑥「这可以放心」⑦「已回滚当晚的汇总任务」⑧「这没有动原始账」⑨「这能从根上堵住同类问题」⑩「它只提示不拦截」。
- **U5 排查记录（陷阱：正确纠正必须保住 + 真绕法要拆）**：必须保住的正确判断①「不是过滤条件写反，是恢复操作没有清掉 void_reason……被导出侧跳过」②「也不是行数上限，是恢复入口只回写了 voided 这一位」③「这不算实现缺陷，而是当时为审计留痕有意安排的」；要拆的真绕法「之所以恢复时没顺手清掉，不是因为没想到，而是当时判断清空不该由恢复入口做，该由独立对账步骤做，而这个步骤一直没排上」（三层转折）。
- **U6 修复指引（陷阱：命令/代码/路径/报错原文逐字保留）**：五条命令行、示例输出「房租<TAB>24000<TAB>1,5」、报错原文 `unknown expense id`、代码行 `groups.setdefault((row['title'], row['cents']), []).append(row['id'])`、路径与验收数（total_cents 36600、当前 72700、多算 36100）都必须原样；夹具 data/ledger.json 与这些数字实跑核对过（dedup 输出三行、void 5/6/7 后 summary=36600）。

## 自检（python3 run.py --check，不调用 codex）

```
prompts ok: 6 cases, single-turn, planned calls 36 (refuse at 190)
unslop sha256 control(a5bfa83)=34faf248e5e4… treatment(worktree)=34faf248e5e4… identical=True
U1–U6: arms are identical (worktree unslop still equals the control revision; expected at freeze time)
self-check: the two arms install byte-identical trees. The worktree skills/unslop/SKILL.md still
equals a5bfa83, which is the state at freeze time. After the four new rules land, rerun --check:
it must report that the arms differ only in .agents/skills/unslop/SKILL.md.
setup ok
```

六题 × 两组共 12 次夹具构建 + 安装全通过；arm_diff_files 的"只允许 unslop 不同"判定用构造差异单测过（unslop 不同→只报 unslop；docs 漂移→报出；完全相同→空）。

## grep 与冻结校验

- 在仓库根目录对本机用户名和本机 home 绝对路径做递归 grep（本机用户名与 <home> 展开后的绝对路径），evaluation/v09/ 下除本报告引用处外无匹配。
- `grep -rniE "mona|hkoption|30sfinance|seedance|seedream|kling|lora|controlnet|wheel|pmcc|condor|strangle|leaps|kelly|hmm|sac|skew|otm|itm|tp80|doh|parquet|launchd|期权|视频生成|抽卡|母脸|…"` 无匹配（完整清单见运行记录，含 79.18/974.70/17.4019 等原句金额标记，均无）。
- 六段 prompt 均不含"说人话/大白话/通俗/别用术语/小白/易懂"（run.py --check 里有硬性断言）。
- `shasum -a 256 -c FREEZE.sha256`：8 行（7 个冻结文件，README.md 补入后重生成）全部 OK。

## 剩下的事（不归这一步）

1. 把四条新规则写进 skills/unslop/SKILL.md（协调者负责）。
2. 重跑 `python3 evaluation/v09/run.py --check`，应报告两组只有 `.agents/skills/unslop/SKILL.md` 不同；不是这个结果不要开跑。
3. 跑真评测（36 次计划调用，重试上限 190），出盲看页给用户定输赢。
