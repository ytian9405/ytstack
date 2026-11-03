# 给发布周报的人留的草稿

我们有个 briefctl 的导出发布流程，主要是为了将 review 环境里的十月份数据整理成一个 CSV 给审阅者，背景解释和操作现在都揉在这里了。以下只是已有流程的说明，不需要你实际执行。服务器上要有 Python 3.11，命令要从 /srv/briefcase 运行，先建好 exports 目录。REPORT_TOKEN 由值班人员预先配置。不要在日志里打印 token。使用的配置是 profiles/review.toml，不要换到 prod。

第一步通常通过 `briefctl inspect --profile review --json` 获得健康报告。这里 healthy 必须是 true，并且 pending_count 必须等于 0；只是命令退出 0 并不够。如果字段不满足，停止后面的步骤，处理积压或健康问题后重新 inspect，不能用后续命令绕过。

在检查满足之后运行 `briefctl export --profile review --since 2026-10-01 --until 2026-11-01 --output exports/october.csv`，日期是左闭右开，所以导出的是 2026 年十月份，而不是把 11 月 1 日也算进去。导出命令必须退出 0。它只生成本地文件，不会自动发布。文件已经存在时，工具会报错退出，不能为了通过而删掉旧文件或增加 --force，先停止并确认旧文件归属；获准处理旧文件后，必须从 inspect 开始重新检查。

导出成功之后，要运行 `briefctl verify --input exports/october.csv --json`。它返回 valid 和 row_count。必须退出 0 且 valid 为 true 才能继续；row_count 允许为 0，所以不能把“没有数据”自行改成失败。verify 不会修复文件。如果失败，停止发布，确认原因并重新生成文件，不允许手改 CSV 来伪造通过结果。

真正发布前还有一次预览：`briefctl publish --profile review --input exports/october.csv --dry-run`。这个 dry-run 会校验发布参数并显示目标位置，但不上传文件，也不创建远程记录。它也必须退出 0。预览失败就停止。预览成功后才运行 `briefctl publish --profile review --input exports/october.csv`。只有最后这一条的退出码为 0 且输出中出现 publish_id，才算发布成功；只有退出 0、没有 publish_id 仍不算成功，不要马上重试发布以免重复创建，先让值班人员核实远端结果。

成功后把 CSV 路径、row_count 和 publish_id 交给审阅者。不需要附 token。这个指南只写到交接为止；数据内容怎样审核是另一份流程。
