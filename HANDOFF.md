# 在另一台电脑上继续

## 现在到哪了

- **新技能（0.5.0）：** 新增 `in-your-own-words`、`ketchup`、`teach`，改编自 pstack。
  - v07 盲看 4 胜 3 负，详见 [evaluation/v07/REPORT.md](evaluation/v07/REPORT.md)。
  - v08 改了输掉的三处：交接写成能照着做的步骤、`teach` 允许一句比方并点出容易误解的后果、复述改成分条写。同时修好了 `ketchup` 的误触发。v08 盲看 6 题全胜，详见 [evaluation/v08/REPORT.md](evaluation/v08/REPORT.md)。
  - 本机 Codex 已经通过 `~/.agents/skills` 的链接用上了这个版本。
- **验收标准：** v0.5 保留，详见 [evaluation/v05/REPORT.md](evaluation/v05/REPORT.md)。
- **说人话：** `voice/plain-talk.md` 是 v0.4 加 4 条新偏好，**还没盲看过**。
- **规则依据：** 全部来自 [voice/PREFERENCES.md](voice/PREFERENCES.md)。

## 下一步，按要紧程度

1. **给现在的说人话规则做盲看。** 对照组用 `evaluation/snapshots/v04`，旧题不能再用，每轮 4 到 8 题。
2. **装进 1 到 2 个真实项目试用。** 装法见 [README.md](README.md)，加 `--voice` 才会写入常驻规则。`ketchup` 的回来汇报和接手这两种用法，v08 没有重新测，用的时候留意。
3. **自主程度的偏好还没有地方放。** 比如“按风险决定停不停”“别一直轮询”。

## 评测需要的环境

- **Codex CLI：** 能用 `gpt-6.1-sol` 和 `gpt-6-astra`。Astra 在并发高时容易超时，所以 `evaluation/v02/harness.py` 限制它同时只跑 2 个。
- **pi：** 带 `zai-coding-cn/glm-5.3-flash`，用来分析对话记录。
- **Python 3.9 以上**，只用标准库。解压 `.jsonl.zst` 需要 `zstandard` 包，或 Node 22.15 以上的版本。
- **基线快照：** v0.1、v0.2、v0.4 的完整快照在 `evaluation/snapshots/`，评测的对照组从这里安装。

## 注意

- 仓库是公开的。对话原文只放在 `~/.ytstack-prefs/` 这类仓库外的目录，用完删掉。
- 模型评委和你的判断多次不一致，规则好不好最后以你的盲看为准。
