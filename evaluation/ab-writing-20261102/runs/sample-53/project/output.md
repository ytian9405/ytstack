# 十月份数据导出与发布操作指南

本流程将 review 环境中 2026 年十月份的数据导出为 CSV，发布后交给审阅者。流程到交接为止，数据内容审核按另一份流程执行。

## 1. 确认前置条件

- 服务器已安装 Python 3.11。
- 所有命令均从 `/srv/briefcase` 运行，且已建好 `exports` 目录。
- 值班人员已预先配置 `REPORT_TOKEN`。不要在日志中打印 token，也不要在交接时提供 token。
- 使用配置 `profiles/review.toml` 和 `review` 环境，不要切换到 `prod`。

## 2. 检查环境状态

运行：

```bash
briefctl inspect --profile review --json
```

检查返回的健康报告。必须同时满足以下条件才能继续：

- `healthy` 为 `true`。
- `pending_count` 等于 `0`。

仅命令退出码为 `0` 不足以通过检查。任一字段不满足要求时，停止后续操作；处理积压或健康问题后，重新运行 `inspect`。不得用后续命令绕过检查。

## 3. 导出 CSV

检查通过后运行：

```bash
briefctl export --profile review --since 2026-10-01 --until 2026-11-01 --output exports/october.csv
```

日期范围为左闭右开，即包含 `2026-10-01`，不包含 `2026-11-01`，导出的是 2026 年十月份的数据。

导出命令必须以退出码 `0` 结束才能继续。该命令只生成本地文件，不会自动发布。

如果 `exports/october.csv` 已存在，工具会报错退出。此时停止操作，先确认旧文件归属。不得为使导出通过而删除旧文件或添加 `--force`。获准处理旧文件后，必须从第 2 步的 `inspect` 开始重新检查。

## 4. 验证 CSV

导出成功后运行：

```bash
briefctl verify --input exports/october.csv --json
```

必须同时满足以下条件才能继续：

- 命令退出码为 `0`。
- 返回的 `valid` 为 `true`。

记录返回的 `row_count`，用于交接。`row_count` 允许为 `0`，不能仅因没有数据就判定失败。

`verify` 不会修复文件。验证失败时，停止发布，确认原因并重新生成文件；不得手动修改 CSV 来伪造通过结果。重新生成时仍须遵守前述检查和旧文件处理要求。

## 5. 预览发布

验证通过后运行：

```bash
briefctl publish --profile review --input exports/october.csv --dry-run
```

预览会校验发布参数并显示目标位置，不上传文件，也不创建远程记录。

预览命令必须以退出码 `0` 结束才能继续；预览失败时停止发布。

## 6. 正式发布

预览成功后运行：

```bash
briefctl publish --profile review --input exports/october.csv
```

只有同时满足以下条件，才算发布成功：

- 命令退出码为 `0`。
- 输出中出现 `publish_id`。

未同时满足时，不得判定发布成功。如果退出码为 `0`，但输出中没有 `publish_id`，不要立即重试，以免重复创建远程记录；先请值班人员核实远端结果。

## 7. 交接给审阅者

发布成功后，将以下信息交给审阅者：

- CSV 路径：`/srv/briefcase/exports/october.csv`。
- 验证返回的 `row_count`。
- 发布返回的 `publish_id`。

不要附上 token。
