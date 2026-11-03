# Ledger Lite 实际验收记录

执行日期：2026-11-02（UTC）。环境：Linux，Python 3.12.3。仅使用标准库，未安装依赖。

从当前项目根目录复跑：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_tests.py
```

实际结果：两个命令退出码均为 0。直接执行 unittest 为 8 个测试全部通过（3.037 秒）；证据脚本的独立基线也是 8 个全部通过（2.785 秒）。保留原有 smoke 测试，新增 LL01–LL07 七个行为测试（无效输入通过 subTest 分别验证）。

证据脚本在六个自动清理的临时项目副本中逐项引入错误，M01–M06 全部被预期行为用例的断言检出，六次变异测试均退出 1，未出现测试 ERROR。脚本最终返回 `passed: true`、`mutations_detected: 6`、`mutations_total: 6`。这些是预期失败，不代表原产品失败。

- [基线完整日志](baseline.log)
- [机器可读结果、环境及输入文件哈希](verification.json)
- 各回归日志：`M01_void_included.log`、`M02_trim_title.log`、`M03_reuse_void_id.log`、`M04_accept_zero.log`、`M05_remove_void_record.log`、`M06_overwrite_category_total.log`
- [复用技能、用例映射和判断标准](../.agents/skills/test-ledger-lite/SKILL.md)

未修改 `expense_cli.py`、`README.md` 和 `tests/test_smoke.py`。所有账本状态与变异文件使用临时目录，正常执行后自动清理；持久保留的证据仅在本目录。

覆盖最重要的添加、列表、作废、汇总、跨进程持久化和输入拒绝行为。未覆盖合同明确排除的损坏 JSON、并发和权限异常，也未验证性能、海量数据、其他 Python 版本或其他操作系统。六个定向变异只证明对应回归可检测，不代表穷尽所有错误。
