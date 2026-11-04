# ytstack

七个个人工作技能、一个随包依赖和一份常驻说话规则。主要为 Codex 的 Sol 和 Astra 调试，同一份源码也可用于 Claude Code。

| 技能 | 用途 |
| --- | --- |
| `in-your-own-words` | 用户点名后，用 3 到 5 句复述目标和要解决的问题，然后停下来等确认。确认过的原文留给验收标准开头、worker 任务卡开头和交接说明的“目的”。 |
| `acceptance-criteria` | 动手前定验收标准：一份连贯的短标准，每条写清靠什么证据算通过，最后列出你可以改的决定。 |
| `create-test-skill` | 为项目生成 `test-<app>` 技能、可运行的行为测试和用例索引，实际运行并证明测试能抓住错误。 |
| `bro` | 把上一条回答说得自然、简明、容易理解。上一条没看懂、我没太明白、我不太理解，用它。问的是某个机制怎么工作，用 `teach`。 |
| `technical-bro` | 按 technical-writing 的四层规范编写或修改技术文档、PR 和提交说明。 |
| `ketchup` | 回来时只汇报、不写文件；要交接说明时写给以后的会话或另一台电脑；接手时先核对写成已完成的，再决定是否继续。 |
| `teach` | 把一个机制讲明白：自己读代码和 git 记录，先给两三句，再用眼前的例子走一遍。 |
| `unslop` | `technical-bro` 和 `teach` 的随包依赖，清理空话和套路表达。 |

`create-test-skill` 用于创建可复用的项目测试能力。普通的一次性测试补充直接使用项目既有 runner。生成测试不会自动授权修改产品代码或共享环境。

## 在项目中使用

在包含 `ytstack/` 的工作区执行以下命令，将技能逐个链接到目标项目。目标项目必须已经存在。

```sh
python3 ytstack/tools/install.py --project /path/to/project --harness codex
```

这会创建项目 `.agents/skills/` 下的八个入口。重新开始会话以刷新技能发现。使用 `$in-your-own-words`、`$create-test-skill`、`$bro`、`$technical-bro`、`$ketchup` 或 `$teach`，也可用自然语言提出对应请求。`in-your-own-words` 只在用户点名时使用。当前会话的技能清单可能不会即时更新。

只安装一个主技能时，可以指定名称；依赖会一起安装。`ketchup` 单独安装，不带其他技能。`teach` 和 `technical-bro` 会带上 `unslop`。

```sh
python3 ytstack/tools/install.py --project /path/to/project --harness codex --skill technical-bro
```

Claude Code 可以直接加载包：

```sh
claude --plugin-dir ./ytstack
```

插件调用名为 `/ytstack:in-your-own-words`、`/ytstack:bro`、`/ytstack:technical-bro`、`/ytstack:create-test-skill`、`/ytstack:ketchup` 和 `/ytstack:teach`。也可以用安装工具暴露为项目技能：

```sh
python3 ytstack/tools/install.py --project /path/to/project --harness claude
```

项目技能位于 `.claude/skills/`，按该宿主的普通技能方式调用。安装器默认使用相对软链接；移动源码包后需要重新连接。需要独立副本时加 `--method copy`。已有不同内容的同名入口会被保留，并返回冲突；不会覆盖。`--dry-run` 只展示计划。

## 让 AI 默认说人话

技能只有被调用时才生效，改变不了第一轮回答。要让每次回答都按读者能懂的方式写，安装时加 `--voice`：

```sh
python3 ytstack/tools/install.py --project /path/to/project --harness codex --voice
```

这会把 [voice/plain-talk.md](voice/plain-talk.md) 写进项目的 `AGENTS.md`（Claude Code 是 `CLAUDE.md`），放在一对标记之间。标记外的内容不变，重复运行不会写第二遍，再次运行会更新标记内的内容。`bro` 继续用于事后补救。

## 请求示例

- “用你的话说说我要干嘛，先别动手。”
- “给 expense 工具加撤销功能，开发前先把验收标准定下来。”
- “用 create-test-skill 给这个 CLI 生成可重复运行的测试技能，验证实际输出和持久化。先证明测试能抓住一次错误，再给我证据。”
- “bro，把上一条解释说成人话，保留数字和必要条件。”
- “technical-bro，把这份文档整理成操作指南，保留真实命令、前置条件和预期结果。”
- “我回来了，现在什么情况？”
- “把我当小白，讲讲这段是怎么工作的。”

`technical-bro` 保留上游英文正文，`unslop` 和 `bro` 在上游内容后增加了中文规则。用户指定的语言、结构和术语优先。

## 检查与来源

包内检查和安装器回归测试只需 Python 3.9+ 标准库：

```sh
python3 ytstack/tools/validate.py
python3 -m unittest discover -s ytstack/tests -v
claude plugin validate ./ytstack
```

第三条需要本机已有 Claude CLI。它验证插件结构，不能代替真实模型行为检查。技能另经过 skill-creator 的元数据检查及独立代理前向试用；结果与未覆盖范围见 `evaluation/`，v0.2 的效果见 [evaluation/v02/REPORT.md](evaluation/v02/REPORT.md)，第二轮盲看见 [evaluation/v03/REPORT.md](evaluation/v03/REPORT.md)，第三轮见 [evaluation/v04/REPORT.md](evaluation/v04/REPORT.md)，三个沟通技能见 [evaluation/v07/REPORT.md](evaluation/v07/REPORT.md) 和 [evaluation/v08/REPORT.md](evaluation/v08/REPORT.md)。规则依据的用户偏好见 [voice/PREFERENCES.md](voice/PREFERENCES.md)。验收标准见 [ACCEPTANCE.md](ACCEPTANCE.md)。

来源、许可证和改动边界见 [NOTICE.md](NOTICE.md) 与 `provenance.json`。本包不安装全局技能，不包含总路由器、模型配置或自动启动 hooks。
