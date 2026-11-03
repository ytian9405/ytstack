已完成，产物均位于指定 project：

- 测试技能：`.agents/skills/test-ledger/SKILL.md`
- 行为测试：`tests/test_behavior.py`
- 缺陷检测脚本：`scripts/check_test_detection.py`
- 复跑说明：`TESTING.md`
- 实际证据：`test-results/`

运行命令：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_test_detection.py
```

实际结果：8 项测试通过，包含保留的原有 smoke 测试；6 个临时植入缺陷全部被检出，临时副本已清理。未修改 `expense_cli.py` 或 `README.md`。

覆盖持久化、添加、作废、ID、汇总、Unicode、输入校验及错误后的数据保护。未覆盖损坏 JSON、并发、权限异常、性能和跨平台验证。
