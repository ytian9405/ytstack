# 导出并发布 2026 年十月份的 review 数据

## 准备运行环境

开始前，确认以下条件已满足：

- 服务器已安装 Python 3.11。
- 所有命令都从 `/srv/briefcase` 运行。
- 已创建 `exports` 目录。
- 值班人员已配置 `REPORT_TOKEN`。不要在日志中打印 token。
- 使用 `profiles/review.toml` 配置。不要切换到 `prod`。

## 检查、导出并发布

按以下顺序操作。只有当前步骤满足继续条件，才能执行下一步。

1. 检查 review 环境。

   ```bash
	briefctl inspect --profile review --json
   ```

   确认健康报告中的 `healthy` 为 `true`，且 `pending_count` 为 `0`。仅命令退出码为 `0` 不够。

   如果字段不满足条件，停止后续步骤。处理积压或健康问题后，重新运行 `inspect`。不要用后续命令绕过检查。

2. 导出十月份的数据。

   ```bash
	briefctl export --profile review --since 2026-10-01 --until 2026-11-01 --output exports/october.csv
   ```

   日期范围左闭右开，包含 2026 年 10 月 1 日，不包含 11 月 1 日。确认命令退出码为 `0`。此命令只生成本地文件，不会自动发布。

   如果文件已存在，工具会报错退出。先停止并确认旧文件归属。不要为通过导出而删除旧文件或增加 `--force`。获准处理旧文件后，必须从第 1 步的 `inspect` 开始重新检查。

3. 验证导出的 CSV。

   ```bash
	briefctl verify --input exports/october.csv --json
   ```

   确认命令退出码为 `0`，且返回的 `valid` 为 `true`。记录返回的 `row_count`。`row_count` 允许为 `0`，不要将没有数据判为失败。

   `verify` 不会修复文件。如果验证失败，停止发布。确认原因后重新生成文件，不要手改 CSV 来伪造通过结果。

4. 预览发布。

   ```bash
	briefctl publish --profile review --input exports/october.csv --dry-run
   ```

   此命令校验发布参数并显示目标位置，不上传文件，也不创建远程记录。确认命令退出码为 `0`。如果预览失败，停止发布。

5. 预览成功后，发布 CSV。

   ```bash
	briefctl publish --profile review --input exports/october.csv
   ```

   只有命令退出码为 `0`，且输出中出现 `publish_id`，才算发布成功。

   如果退出码不为 `0`，不要判为成功。如果退出码为 `0`，但没有 `publish_id`，也不算成功。此时不要立即重试发布，以免重复创建记录。先让值班人员核实远端结果。

## 将发布结果交给审阅者

确认发布成功后，将以下信息交给审阅者：

- CSV 路径 `exports/october.csv`，运行目录为 `/srv/briefcase`。
- 验证返回的 `row_count`。
- 发布返回的 `publish_id`。

不要附上 token。交接后结束本流程，数据内容审核按另一份流程执行。
