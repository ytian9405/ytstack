# 温度记录小工具

`temp_log.py` 记探头温度，读数放在 `--state` 指定的 json 文件里。探头要先登记：`logger.json` 的 `sensors` 里写上编号和名字，没登记的编号会被拒收。`report_hour` 和 `csv_dir` 是日报配置，日报脚本不在本仓库。

- 记数：`add S1 21.5`，可用 `--at` 指定时间
- 看数：`list`
- 统计：`stats --sensor S1`

```sh
python3 tests/test_smoke.py
```
