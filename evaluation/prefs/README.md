# 从对话记录里找偏好

这里的工具用来更新 [voice/PREFERENCES.md](../../voice/PREFERENCES.md)。流程照 pstack 的 `automate-me`：从本人的对话记录里找反复出现的反应，分时间段交叉核对，再直接问本人，最后才改规则。

## 1. 抽出你自己发的消息

```sh
python3 evaluation/prefs/mine.py --codex-home ~/.codex --out ~/.ytstack-prefs
```

- 有多个 Codex 目录时，重复写 `--codex-home`。例如 Windows 版在 WSL 里是 `/mnt/c/Users/<用户名>/.codex`。
- 会读取 `sessions/` 和 `archived_sessions/`，压缩的 `.jsonl.zst` 会自动解压到临时目录。解压需要 Python 的 `zstandard` 包，或 Node 22.15 以上的版本。
- 子代理、定时任务和评测沙盒的会话会被去掉，只留你本人打的字，每条附上它前面那条 AI 回复。
- 输出默认在 `~/.ytstack-prefs/`，不在仓库里，因为里面是你对话的原文。分成 3 个按时间排序的片段，外加分析用的 `prompt.md`。

## 2. 让 pi 分析每一段

```sh
cd ~/.ytstack-prefs
for s in 1 2 3; do
  pi -p --no-session --no-tools --approve --model zai-coding-cn/glm-5.3-flash --thinking max \
    @prompt.md @slice$s.md "按附件 prompt.md 的要求分析附件 slice$s.md。" </dev/null > out$s.md &
done
wait
```

每段大约 10 万字时要跑 5 到 10 分钟。`--approve` 让 pi 信任当前目录，`--no-tools` 保证它只读附件、不运行命令。

## 3. 核对引文

```sh
for s in 1 2 3; do python3 /path/to/ytstack/evaluation/prefs/check_quotes.py slice$s.md out$s.md; done
```

上次 300 多条引文里有 95% 以上能在原文找到，没对上的多半是标点不同。没对上的条目要看原文，不要直接采信。

## 4. 合并进偏好文件

- 只有在两个以上时间段都出现的偏好，才写进 `PREFERENCES.md` 的正文。只出现一次的放进“待确认”。
- 写进去的是你的原话和次数，不含项目里的具体数据。仓库是公开的。
- 改完偏好，再改 `voice/plain-talk.md` 或 `skills/acceptance-criteria/SKILL.md`，然后用新题跑一轮盲看，见 [../v04/run.py](../v04/run.py)。
- 分析完删除 `~/.ytstack-prefs/`。
