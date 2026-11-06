# 两个小工具

`queue_cli.py` 记本地待办。`expense_cli.py` 记本地账，金额用分。从本目录运行，状态文件由 `--state` 指定。

- 待办：`add`、`list`、`complete`
- 账本：`add`、`list`、`void`、`summary`
- `summary` 只把没作废的算进合计

```sh
python3 tests/test_smoke.py
```
