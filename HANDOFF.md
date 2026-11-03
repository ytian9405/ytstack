# 在另一台电脑上继续

## 现在到哪了

v0.5 已经过你的盲看，详见 [evaluation/v05/REPORT.md](evaluation/v05/REPORT.md)。

- **验收标准：** v0.5 对 v0.4 是 1 胜 1 平，保留。模型评分里，Sol 拒绝错误实现从 16/20 升到 20/20。
- **说人话：** v0.5 输给 v0.4，1 胜 3 负，因为写短时把理由删了。现在的 `voice/plain-talk.md` 以 v0.4 为底，加了 4 条新偏好：用中文、职业视角只在点名时用、你复述理解时只判对错、写短时不删理由。这一版**还没盲看过**。
- **规则依据：** 全部来自 [voice/PREFERENCES.md](voice/PREFERENCES.md)，最近一次在 2026-11-03 用 Mac 上的 9260 条消息更新过。

## 下一步，按要紧程度

1. **给现在的说人话规则做盲看。** 对照组用 `evaluation/snapshots/v04`。先在 `evaluation/v06/prompts.json` 冻结新题，照 [evaluation/v05/run.py](evaluation/v05/run.py) 跑。旧题不能再用，每轮 4 到 8 题。
2. **装进 1 到 2 个真实项目试用。** 装法见 [README.md](README.md)，加 `--voice` 才会写入常驻规则。
3. **自主程度的偏好还没有地方放。** 比如“按风险决定停不停”“别一直轮询”，这些不归说人话规则管，可以考虑做成单独的常驻规则。

## 评测需要的环境

- **Codex CLI：** 能用 `gpt-6.1-sol` 和 `gpt-6-astra`。Astra 在并发高时容易超时，所以 `evaluation/v02/harness.py` 限制它同时只跑 2 个。
- **pi：** 带 `zai-coding-cn/glm-5.3-flash`，用来分析对话记录。
- **Python 3.9 以上**，只用标准库。解压 `.jsonl.zst` 需要 `zstandard` 包，或 Node 22.15 以上的版本。
- **基线快照：** v0.1、v0.2、v0.4 的完整快照在 `evaluation/snapshots/`，评测的对照组从这里安装。

## 注意

- 仓库是公开的。对话原文只放在 `~/.ytstack-prefs/` 这类仓库外的目录，用完删掉。
- 模型评委和你的判断多次不一致，规则好不好最后以你的盲看为准。
