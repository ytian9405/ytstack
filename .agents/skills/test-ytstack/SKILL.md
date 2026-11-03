---
name: test-ytstack
description: "Run ytstack package and installer acceptance tests with case IDs, CLI evidence, isolated dependency failure detection, and cleanup checks. Use to verify ytstack installation or changes to its manifest, installer, skill resources, and package validation. Does not evaluate model writing quality or native host skill discovery."
---

# 测试 ytstack 安装行为

在包含 `tools/install.py`、`ytstack.json`、`tests/test_package.py` 的仓库根目录执行以下命令。测试代码在 `tests/ytstack_skill/`，无需读取生成器或历史聊天，也无需全局安装 ytstack。移动仓库后，命令仍使用相对路径。

## 准备并检查目标

需要 Python 3.9+ 和支持软链接的本地文件系统。测试只使用标准库，不需要网络、账号、服务器、端口或后台进程。CLI 每次调用启动一个进程，并等待它退出。

先为本次证据选择一个从未使用的目录。以下命令使用 `evaluation/self-test/manual-01/`。重跑时更换目录名，保留旧记录。

```sh
python3 tests/ytstack_skill/run.py --doctor --evidence evaluation/self-test/manual-01/doctor.json
```

Doctor 检查 Python 版本、目标文件、包版本及安装器的 `--help` 是否成功退出。它不安装技能、不启动服务，也不代表行为测试通过。Doctor 会写指定的证据文件。缺少前置条件时，停止行为测试，报告 `BLOCKED` 并附上证据。

## 运行用例

运行全部 10 个用例：

```sh
python3 tests/ytstack_skill/run.py --evidence evaluation/self-test/manual-01/suite.json
```

只验证依赖补齐和重复安装：

```sh
python3 tests/ytstack_skill/run.py --case YT02 --evidence evaluation/self-test/manual-01/YT02.json
```

[用例索引](cases/README.md)列出每个输入、操作、预期结果和独立运行命令。原有 unittest 入口仍可运行，但不生成完整 CLI 记录：

```sh
python3 -m unittest discover -s tests -v
```

每个 CLI 子进程最长运行 15 秒。完整测试正常执行时调用 12 次安装器或验证器，另有一次 Doctor 检查。若所有这些调用都用满等待时间，合计为 195 秒，另加本地文件操作时间。测试不依赖外部 `timeout` 命令。

## 证明测试能抓错

运行以下命令，创建临时包副本，在副本中让依赖安装失效，再恢复副本。用户工作区的产品源码不变。

```sh
python3 tests/ytstack_skill/prove_failure_detection.py --evidence-dir evaluation/self-test/manual-01/failure-detection
```

脚本连续执行完全相同的 YT02 命令。预期原版 `PASS`、坏副本 `FAIL`、恢复版 `PASS`，退出码依次为 0、1、0。坏副本仍成功安装 `technical-bro` 并返回 0，但安装结果缺少 `unslop`。YT02 必须在内容断言上失败；语法错误或依赖无法启动不能算成功抓错。

`proof.json` 记录验证结论。`mutation.patch`、`broken-install.py`、三阶段 JSON 和标准输出、错误日志保留在证据目录。故障验证的每阶段最长等待 45 秒。预期的坏副本失败不等于正式目标存在缺陷。

## 解释结果并保留证据

运行器退出码为 0 `PASS`、1 `FAIL`、2 `BLOCKED`、3 `SKIPPED`。无效参数也可能由 argparse 返回 2，此时不会产生测试结果文件，不能当作已执行用例。

JSON 包含命令、工作目录、Python 和目标包版本、产品文件 SHA-256、稳定用例 ID、逐次 CLI 输出及退出码、断言失败堆栈、临时目录清理结果。成功意味着该用例的 unittest 断言通过；不宣称未执行的覆盖。运行器拒绝覆盖已有证据文件。

`FAIL` 表示行为断言失败。保留断言和现场证据，报告问题，不修改产品代码或降低预期。`BLOCKED` 表示环境缺少必要条件或进程超时。若某用例尚未运行，标记 `SKIPPED` 并写明原因。技能文件检查和真实产品结果分别报告。

## 清理并维护

每个用例仅使用自己创建的 `ytstack-test-` 临时目录，退出上下文时清理，断言失败时也执行。故障验证另有一个自己创建的 `ytstack-negative-` 临时目录，脚本退出时清理。所有子进程均同步等待；超时由 subprocess 终止并回收。没有常驻进程需要停止。

检查结果中的 `cleanup_passed`、`target_unchanged`，以及故障验证中的 `scratch_removed`、`live_target_unchanged`。证据在仓库的 `evaluation/self-test/` 下，位于临时目录之外，清理后仍应存在。不要按名称批量杀进程，也不要按临时目录前缀批量删除。

变更安装器或清单后重跑 YT02–YT08。变更技能资源、来源记录或许可证后重跑 YT01 和 YT05。修改测试映射时同步更新本技能及用例索引。若故障补丁位置变化，先审查脚本再更新，保持预期不变。

本技能覆盖安装器 CLI 和包验证入口。它验证 Codex 与 Claude 的目标目录布局，未验证宿主真实发现或模型调用，也未评估 `bro`、`technical-bro` 的写作效果。平台权限失败、并发安装、安装中途磁盘错误、其他 Python 版本尚未覆盖。
