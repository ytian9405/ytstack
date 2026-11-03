# 在另一台电脑上继续

## 现在到哪了

v0.4 已经过三轮你的盲看，详见 [evaluation/v04/REPORT.md](evaluation/v04/REPORT.md)。

- **验收标准：** 新版第一次赢了改动前的写法，2 比 0。
- **说人话：** v0.2 比改动前好（4 比 2）。之后两版都只和 v0.2 打平，v0.4 把长度控制回了约 425 字。
- **规则依据：** 全部来自 [voice/PREFERENCES.md](voice/PREFERENCES.md)，这些偏好来自这台电脑上 3 周的 Codex 记录，共 291 条你本人发的消息。

## 下一步，按要紧程度

1. **用那台电脑的记录更新偏好。** 按 [evaluation/prefs/README.md](evaluation/prefs/README.md) 抽消息、让 pi 分析、核对引文，只把多个时间段都出现的偏好写进 `voice/PREFERENCES.md`。
2. **改规则。** 说人话的改动写进 `voice/plain-talk.md`，验收的改动写进 `skills/acceptance-criteria/SKILL.md`。每条规则都要能在 `PREFERENCES.md` 里找到依据。
3. **验收标准抓错误的能力要补。** 模型评分里，新版拒绝错误实现的比例比改动前略低：Sol 是 13/20 对 15/20。补的时候注意别把篇幅写回去。
4. **用新题盲看。** 先在 `evaluation/v05/prompts.json` 冻结新题，再改规则，然后照 [evaluation/v04/run.py](evaluation/v04/run.py) 跑，最后用 `human-review/blind-review.html` 盲看。旧题不能再用。
5. **装进 1 到 2 个真实项目试用。** 装法见 [README.md](README.md)，加 `--voice` 才会写入常驻规则。

## 评测需要的环境

- **Codex CLI：** 能用 `gpt-6.1-sol` 和 `gpt-6-astra`。Astra 在并发高时容易超时，所以 `evaluation/v02/harness.py` 限制它同时只跑 2 个。
- **pi：** 带 `zai-coding-cn/glm-5.3-flash`，用来分析对话记录。
- **Python 3.9 以上**，只用标准库。解压 `.jsonl.zst` 需要 `zstandard` 包，或 Node 22.15 以上的版本。
- **基线快照：** v0.1 和 v0.2 的完整快照在 `evaluation/snapshots/`，评测的对照组从这里安装。

## 注意

- 仓库是公开的。对话原文只放在 `~/.ytstack-prefs/` 这类仓库外的目录，用完删掉。
- 模型评委和你的判断多次不一致，规则好不好最后以你的盲看为准。
