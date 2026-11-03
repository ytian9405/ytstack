已完成，未修改 `expense_cli.py`、README 产品合同或原有测试。

产物位于指定 project：

- 技能：`.agents/skills/test-ledger-lite/SKILL.md`
- 用例索引：`.agents/skills/test-ledger-lite/cases/README.md`
- 行为测试：`tests/test_behaviors.py`
- 执行说明：`evidence/README.md`
- 最终日志及故障补丁：`evidence/20261102T124105239011Z/`

在 project 根目录复跑：

```sh
python3 -m unittest discover -s tests -v
python3 .agents/skills/test-ledger-lite/scripts/run_evidence.py
```

实际结果：新增五组行为测试及原有 smoke 测试共 6 项全部通过，包括 7 个非法操作子用例。隔离副本丢弃磁盘写入后，持久化内容断言按预期失败；随后原项目复跑全部通过。临时状态已清理，证据保留。

未覆盖：损坏 JSON、并发写入、权限异常，以及穷举金额边界、Unicode 和参数错误组合。
