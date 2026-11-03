# 导出并发布 2026 年 10 月 review 数据

本流程将 review 环境中 2026 年 10 月的数据导出为 CSV，发布后交给审阅者。流程到交接为止，数据内容审核按另一份流程执行。

## 操作前准备

- 确认服务器已安装 Python 3.11。
- 从 `/srv/briefcase` 目录运行所有命令，并预先创建 `exports` 目录。
- 确认值班人员已配置 `REPORT_TOKEN`。不要在日志中打印 token，也不要在交接时附上 token。
- 使用 `profiles/review.toml` 配置和 `review` 环境，不要切换到 `prod`。

## 1. 检查环境状态

运行：

```bash
briefctl inspect --profile review --json
```

检查返回的 JSON，只有同时满足以下条件才能继续：

- `healthy` 为 `true`。
- `pending_count` 等于 `0`。

命令退出码为 `0` 本身不足以通过检查。任一字段不满足时，停止后续步骤；处理积压或健康问题后重新运行 `inspect`，不得用后续命令绕过检查。

## 2. 导出 CSV

检查通过后运行：

```bash
briefctl export --profile review --since 2026-10-01 --until 2026-11-01 --output exports/october.csv
```

日期范围为左闭右开，即包含 2026 年 10 月 1 日，不包含 2026 年 11 月 1 日。

导出命令必须以退出码 `0` 结束。此命令只生成本地文件，不会自动发布。

如果 `exports/october.csv` 已存在，工具会报错退出。此时停止操作，先确认旧文件归属，不得为了通过而删除旧文件或增加 `--force`。获准处理旧文件后，必须从第 1 步 `inspect` 开始重新检查。

## 3. 验证 CSV

导出成功后运行：

```bash
briefctl verify --input exports/october.csv --json
```

只有退出码为 `0` 且返回的 `valid` 为 `true`，才能继续。记录返回的 `row_count`；`row_count` 允许为 `0`，不要将“没有数据”自行判定为失败。

`verify` 不会修复文件。验证失败时，停止发布，确认原因并重新生成文件，不得手动修改 CSV 来伪造通过结果。

## 4. 预览发布

验证通过后运行：

```bash
briefctl publish --profile review --input exports/october.csv --dry-run
```

此命令校验发布参数并显示目标位置，不上传文件，也不创建远程记录。

退出码必须为 `0`。预览失败时停止操作；只有预览成功后才能正式发布。

## 5. 正式发布并判断结果

运行：

```bash
briefctl publish --profile review --input exports/october.csv
```

只有同时满足以下条件，才算发布成功：

- 退出码为 `0`。
- 输出中出现 `publish_id`。

如果退出码为 `0`，但没有 `publish_id`，仍不算发布成功。不要立即重试发布，以免重复创建；先请值班人员核实远端结果。

## 6. 交接给审阅者

确认发布成功后，将以下信息交给审阅者：

- CSV 路径：`exports/october.csv`（位于 `/srv/briefcase` 下）。
- 验证返回的 `row_count`。
- 发布返回的 `publish_id`。

不要附上 token。
