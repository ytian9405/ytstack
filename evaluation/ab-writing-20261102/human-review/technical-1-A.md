# 导出并发布 review 环境的十月份数据

## 准备运行环境

运行前，确认以下条件已满足：

- 服务器已安装 Python 3.11。
- 所有命令都从 `/srv/briefcase` 运行。
- `exports` 目录已创建。
- 值班人员已预先配置 `REPORT_TOKEN`。不要在日志中打印 token。
- 使用 `profiles/review.toml` 配置和 `review` 环境，不要切换到 `prod`。

## 1. 检查环境健康状态

运行健康检查：

```bash
briefctl inspect --profile review --json
```

检查 JSON 输出。只有 `healthy` 为 `true` 且 `pending_count` 等于 `0`，才能继续。命令退出码为 `0` 不足以判定检查通过。

如果任一字段不满足条件，停止后续步骤。处理积压或健康问题后，重新运行 `inspect`。不要用后续命令绕过检查。

## 2. 导出十月份数据

健康检查通过后，运行导出命令：

```bash
briefctl export --profile review --since 2026-10-01 --until 2026-11-01 --output exports/october.csv
```

日期范围包含 `2026-10-01`，不包含 `2026-11-01`，导出的数据属于 2026 年十月份。

只有导出命令退出码为 `0`，才能继续。此命令只生成本地文件，不会自动发布。

如果 `exports/october.csv` 已存在，工具会报错退出。停止操作，先确认旧文件归属。不要为通过导出而删除旧文件或增加 `--force`。获准处理旧文件后，必须从第 1 步的 `inspect` 重新检查。

## 3. 验证 CSV

导出成功后，运行验证命令：

```bash
briefctl verify --input exports/october.csv --json
```

只有命令退出码为 `0` 且输出中的 `valid` 为 `true`，才能继续。记录输出中的 `row_count`。`row_count` 允许为 `0`，不要把没有数据判为失败。

`verify` 不会修复文件。如果验证失败，停止发布。确认原因后重新生成文件，不要手动修改 CSV 来伪造通过结果。

## 4. 预览发布

验证通过后，运行发布预览：

```bash
briefctl publish --profile review --input exports/october.csv --dry-run
```

此命令校验发布参数并显示目标位置，不上传文件，也不创建远程记录。

只有命令退出码为 `0`，才能继续。预览失败时，停止发布。

## 5. 发布 CSV

预览成功后，运行正式发布命令：

```bash
briefctl publish --profile review --input exports/october.csv
```

只有命令退出码为 `0` 且输出中出现 `publish_id`，才算发布成功。

如果退出码为 `0`，但输出中没有 `publish_id`，仍不能判定发布成功。不要立即重试，以免重复创建远程记录。先让值班人员核实远端结果。

## 6. 交接给审阅者

发布成功后，将以下信息交给审阅者：

- CSV 路径 `exports/october.csv`，文件位于 `/srv/briefcase` 下。
- 验证输出中的 `row_count`。
- 发布输出中的 `publish_id`。

不需要附上 token。交接后，按另一份流程审核数据内容。
