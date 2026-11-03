# Ledger Lite

Ledger Lite 是一个使用 Python 3.9+ 标准库的本地记账 CLI。无需安装依赖、网络、账号或服务器。从本项目根目录运行：

```sh
python3 expense_cli.py --state /tmp/my-ledger.json add "午餐" --cents 1250 --category food
python3 expense_cli.py --state /tmp/my-ledger.json list
python3 expense_cli.py --state /tmp/my-ledger.json void 1
python3 expense_cli.py --state /tmp/my-ledger.json summary
```

每条成功命令输出一个 JSON 值，退出码为 0。

- `add` 返回完整记录，字段为 `id`、`title`、`cents`、`category`、`voided`。首个 ID 为 1，随后单调递增，不因作废而复用 ID。标题和类别保留原始字符串，包括 Unicode 和首尾空格。金额以正整数分表示，新记录的 `voided` 为 `false`。
- `list` 按添加顺序返回所有记录，包括作废记录。添加及作废必须跨独立进程持久化。
- `void ID` 保留记录的 ID、标题、金额和类别，将 `voided` 改为 `true`，并返回完整记录。重复作废同一记录无额外副作用。
- `summary` 仅统计未作废记录，返回 `count`（记录数）、`total_cents`（金额合计）和 `by_category`（类别到金额合计的对象）。空账本的结果为 `{"count": 0, "total_cents": 0, "by_category": {}}`。
- 缺失状态文件表示空账本，`list` 返回 `[]`。首次写入自动创建状态文件的父目录。读取空账本不创建状态文件。
- 非整数或非正数金额、全空白标题、全空白类别，以及不存在的作废 ID，必须非零退出并向 stderr 输出错误，已有数据不变。

每次测试使用独立状态路径。现有测试使用 unittest，运行入口为：

```sh
python3 -m unittest discover -s tests -v
```

损坏的 JSON 文件、并发写入和文件系统权限异常不在当前产品合同中。
