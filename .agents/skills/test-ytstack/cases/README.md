# ytstack 用例索引

依据仓库 `README.md` 的安装说明和 `ACCEPTANCE.md` 的安装约定编写。所有命令从仓库根目录执行，证据文件必须使用新路径。各用例在 `tests/test_package.py` 中，通过真实 CLI 执行，不调用产品内部函数。

| ID | 输入和用户操作 | 独立预期结果 | unittest 方法 |
| --- | --- | --- | --- |
| YT01 | 执行包验证器 | 退出 0，JSON 的 status 为 PASS | `test_package_integrity` |
| YT02 | 对空临时项目安装 technical-bro 两次 | 第一次仅有 technical-bro 和 unslop；依赖可读；第二次 installed 为空、unchanged 为 2 | `test_dependency_is_installed_and_repeat_is_harmless` |
| YT03 | 预置内容为 `my existing skill` 的同名技能，再安装 technical-bro | 非零退出，原内容保留，unslop 未被部分安装 | `test_conflict_is_preserved_without_partial_installation` |
| YT04 | 对空临时项目执行默认 dry-run | 计划 5 个入口，不创建 .agents 目录 | `test_dry_run_changes_nothing` |
| YT05 | 向 Claude 目录复制安装两次，再移走源码包 | 安装 5 个技能、再次安装无变化；移走源码后所有资源字节保持一致，依赖和许可证仍可读 | `test_copied_claude_skills_are_standalone` |
| YT06 | 先用软链接安装 bro，再尝试 copy | 非零退出，原软链接保留，不把它报告成独立副本 | `test_copy_does_not_claim_a_link_is_standalone` |
| YT07 | 项目的 .agents 指向项目外的共享目录，再安装 | 非零退出，共享目录没有新增内容 | `test_project_install_does_not_follow_discovery_outside_project` |
| YT08 | 分别为 Codex 和 Claude 默认安装，再一起搬移源码和项目到含空格的目录 | 恰好 5 个指定技能，所有入口是相对软链接，移动后资源及 unslop 依赖仍可读 | `test_default_links_survive_bundle_move_for_both_hosts` |
| YT09 | 已有 AGENTS.md 时带 `--voice` 安装两次 | 原内容保留在开头，规则写入一次，第二次无变化 | `test_voice_block_keeps_user_content_and_repeat_is_harmless` |
| YT10 | 带 `--voice` 预演；再对含旧规则块的文件安装 | 预演不建文件；旧块被替换，块外内容不变 | `test_voice_dry_run_and_stale_block_update` |

各用例的独立运行命令如下。重跑时更换 `manual-01`，避免覆盖历史证据。

```sh
python3 tests/ytstack_skill/run.py --case YT01 --evidence evaluation/self-test/manual-01/YT01.json
python3 tests/ytstack_skill/run.py --case YT02 --evidence evaluation/self-test/manual-01/YT02.json
python3 tests/ytstack_skill/run.py --case YT03 --evidence evaluation/self-test/manual-01/YT03.json
python3 tests/ytstack_skill/run.py --case YT04 --evidence evaluation/self-test/manual-01/YT04.json
python3 tests/ytstack_skill/run.py --case YT05 --evidence evaluation/self-test/manual-01/YT05.json
python3 tests/ytstack_skill/run.py --case YT06 --evidence evaluation/self-test/manual-01/YT06.json
python3 tests/ytstack_skill/run.py --case YT07 --evidence evaluation/self-test/manual-01/YT07.json
python3 tests/ytstack_skill/run.py --case YT08 --evidence evaluation/self-test/manual-01/YT08.json
```

YT01 复用产品自带验证器，覆盖结构和来源完整性，不独立证明安装行为。YT02–YT08 使用独立的文件内容、集合、路径和退出状态断言。故障验证保持 YT02 的预期不变，只在临时副本中漏装 unslop。
