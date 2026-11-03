# create-test-skill 自测结果

本轮在 ytstack 自身使用 `create-test-skill`，生成项目技能 [test-ytstack](../../.agents/skills/test-ytstack/SKILL.md)。实际测试安装器 CLI 和包验证入口。产品代码未修改。

完整结论见 [summary.json](summary.json)。结果分别记录如下：

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 生成技能的元数据、链接和 8 个用例映射 | PASS | [artifact-validation.json](artifact-validation.json) |
| 当前工作区的实际行为 | 8/8 PASS，12 次 CLI 调用 | [generation/suite.json](generation/suite.json) |
| 代表性故障检测 | 原版 PASS、漏装 unslop 的副本 FAIL、恢复后 PASS | [proof.json](generation/failure-detection/proof.json) |
| 缺少目标的环境检查 | 正确返回 BLOCKED，未执行行为用例 | [missing-target.json](generation/missing-target.json) |
| 独立新会话复验 | Doctor、8 个用例、单独 YT02、故障检测均通过，无需修订说明 | [COLD-REVIEW.json](cold-01/COLD-REVIEW.json) |
| 清理和源码保护 | 临时状态及外层隔离项目已清理，产品文件未变，归档证据仍在 | [summary.json](summary.json) |

测试保留了原有 7 个 unittest 方法，并加强复制安装用例：移走源码后，安装内容和依赖仍可读取。另新增一个用例，检查 Codex 和 Claude 两种目录布局的默认相对软链接，在一起搬移源码和项目后仍然有效。

故障检测仅修改临时副本。坏副本的安装器仍返回成功，但缺少必须安装的 `unslop`，不变的 YT02 内容断言因此失败。补丁、坏副本源码和三阶段日志均保留在 `generation/failure-detection/` 下。这证明该断言能抓住漏装依赖，不代表能够发现任意缺陷。

独立会话只收到隔离项目和生成技能入口，不继承生成会话，也未读取生成器说明。归档后保留日志中的原始临时路径，外层隔离项目已删除。证据文件经过逐文件哈希比对，归档内容与原始记录一致。

从仓库根目录复跑，使用一个新的证据路径：

```sh
python3 tests/ytstack_skill/run.py --evidence evaluation/self-test/rerun-01/suite.json
```

完整操作、单用例命令和故障验证见生成技能。本轮验证环境为 Linux、Python 3.12.3。未覆盖宿主真实技能发现、模型调用、写作效果、其他 Python 版本、并发安装或安装中途磁盘故障。
