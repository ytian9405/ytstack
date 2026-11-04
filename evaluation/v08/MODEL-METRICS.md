# v08 模型指标

这些数字只作参考。规则能判的用规则。需要读意思的，是人工读原文判的，没有调用 Codex 当评委。

Codex 调用次数：80（到 145 拒绝再调用，上限 150）。

## 隔离和技能版本

每个 codex 子进程使用单独的空 HOME 和单独的 CODEX_HOME。HOME 下没有 .agents。CODEX_HOME 只有复制过来的登录文件和一份最小配置，没有 skills 目录。shell_environment_policy.exclude 含 CODEX_HOME，子进程的 shell 看不到这份目录。没有读取登录文件的内容，也没有改 ~/.agents 或 ~/.codex。

没有加载本机 ~/.codex/config.toml。子进程配置只写了模型、high reasoning、pragmatic、approval_policy=never、sandbox_mode=read-only，以及排除 CODEX_HOME。每次调用仍另传 --sandbox 或 -c sandbox_mode。

H1-astra-control-r1 的 skills_read 读了项目里的 ketchup，命令路径不是全局 ~/.agents/skills，三个 SKILL.md 的 sha256 等于提交 7fb9483。

| 技能 | 对照组 sha256 | 实验组 sha256 | 不同 |
| --- | --- | --- | --- |
| ketchup | `55b72bbc692b9d3dacbafd8b041df29b43b1c09537605491869f999635bf48d2` | `b72c89dcc4fbe1cb5d76174cceed8adc219685a4636606ae52c276d156ef5e11` | 是 |
| teach | `7e99f5948d5027ef42a1fc80c31a4114213fd5335183c272feaa84c676fc76c8` | `9f39cd08935c1378b6e09452ef645b0bf452f9d722da28b3edb8b6b351a82bbf` | 是 |
| in-your-own-words | `1aa9c98e862bdf565099932aa49f72dee190045087a81916adae127d9e154428` | `7b507f53676cfe0f7bf32a0658d28966d8e734bae62fdc482664bba4778a82fa` | 是 |

其余技能的 SKILL.md，两组用的是同一份工作区副本，sha256 相同：

- acceptance-criteria: `9675309356ebfa804dcac5dd7b750f32aa4061a56d0ed1c1e08496eced2f69dd`
- bro: `2fbfa343b08cc82a38ecd72833ab0b281b0bcdb57c01343c4bad4db582f882a9`
- create-test-skill: `e185b2cae914d72668760d22f99141d008276c75d6683cadf4356669420b471e`
- technical-bro: `ed1ad79cf2a71710dbc0cb618c7598508e62c21290f8f982acbd8ed18546c8b5`
- unslop: `34faf248e5e4d72f877c7ed3f48fedf42dfcd64a93375c7ba9752e28be4c13ff`

## 运行状态

| 题 | 组 | 模型 | 次数 | 状态 | 失败原因 |
| --- | --- | --- | --- | --- | --- |
| H1 | control | gpt-6.1-sol | r1 | ok |  |
| H1 | control | gpt-6.1-sol | r2 | ok |  |
| H1 | control | gpt-6-astra | r1 | ok |  |
| H1 | treatment | gpt-6.1-sol | r1 | ok |  |
| H1 | treatment | gpt-6.1-sol | r2 | ok |  |
| H1 | treatment | gpt-6-astra | r1 | ok |  |
| H2 | control | gpt-6.1-sol | r1 | ok |  |
| H2 | control | gpt-6.1-sol | r2 | ok |  |
| H2 | control | gpt-6-astra | r1 | ok |  |
| H2 | treatment | gpt-6.1-sol | r1 | ok |  |
| H2 | treatment | gpt-6.1-sol | r2 | ok |  |
| H2 | treatment | gpt-6-astra | r1 | ok |  |
| T1 | control | gpt-6.1-sol | r1 | ok |  |
| T1 | control | gpt-6.1-sol | r2 | ok |  |
| T1 | control | gpt-6-astra | r1 | ok |  |
| T1 | treatment | gpt-6.1-sol | r1 | ok |  |
| T1 | treatment | gpt-6.1-sol | r2 | ok |  |
| T1 | treatment | gpt-6-astra | r1 | ok |  |
| T2 | control | gpt-6.1-sol | r1 | ok |  |
| T2 | control | gpt-6.1-sol | r2 | ok |  |
| T2 | control | gpt-6-astra | r1 | ok |  |
| T2 | treatment | gpt-6.1-sol | r1 | ok |  |
| T2 | treatment | gpt-6.1-sol | r2 | ok |  |
| T2 | treatment | gpt-6-astra | r1 | ok |  |
| I1 | control | gpt-6.1-sol | r1 | ok |  |
| I1 | control | gpt-6.1-sol | r2 | ok |  |
| I1 | control | gpt-6-astra | r1 | ok |  |
| I1 | treatment | gpt-6.1-sol | r1 | ok |  |
| I1 | treatment | gpt-6.1-sol | r2 | ok |  |
| I1 | treatment | gpt-6-astra | r1 | ok |  |
| I2 | control | gpt-6.1-sol | r1 | ok |  |
| I2 | control | gpt-6.1-sol | r2 | ok |  |
| I2 | control | gpt-6-astra | r1 | ok |  |
| I2 | treatment | gpt-6.1-sol | r1 | ok |  |
| I2 | treatment | gpt-6.1-sol | r2 | ok |  |
| I2 | treatment | gpt-6-astra | r1 | ok |  |

状态合计：ok 36。

## 只读和交接文件

规则：T1、T2、I1、I2 看这一轮前后的指纹。H1、H2 看第二轮是不是只多了一个说明文件（markdown，或文件名里有 HANDOFF / 交接），并且没有改别的、没有新提交。指纹不含 `.git`、`__pycache__`，也不含评测自己写的 `jobs/rollup-progress.json` 和 `jobs/rollup.pid`。

| 运行 | 判定 | 多出的文件 | 改过的文件 | 删掉的文件 |
| --- | --- | --- | --- | --- |
| H1-sol-control-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H1-sol-control-r2 | 只多一份说明 | HANDOFF.md | — | — |
| H1-astra-control-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H1-sol-treatment-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H1-sol-treatment-r2 | 只多一份说明 | HANDOFF.md | — | — |
| H1-astra-treatment-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H2-sol-control-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H2-sol-control-r2 | 只多一份说明 | HANDOFF.md | — | — |
| H2-astra-control-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H2-sol-treatment-r1 | 只多一份说明 | HANDOFF.md | — | — |
| H2-sol-treatment-r2 | 只多一份说明 | HANDOFF.md | — | — |
| H2-astra-treatment-r1 | 只多一份说明 | HANDOFF.md | — | — |
| T1-sol-control-r1 | 没变 | — | — | — |
| T1-sol-control-r2 | 没变 | — | — | — |
| T1-astra-control-r1 | 没变 | — | — | — |
| T1-sol-treatment-r1 | 没变 | — | — | — |
| T1-sol-treatment-r2 | 没变 | — | — | — |
| T1-astra-treatment-r1 | 没变 | — | — | — |
| T2-sol-control-r1 | 没变 | — | — | — |
| T2-sol-control-r2 | 没变 | — | — | — |
| T2-astra-control-r1 | 没变 | — | — | — |
| T2-sol-treatment-r1 | 没变 | — | — | — |
| T2-sol-treatment-r2 | 没变 | — | — | — |
| T2-astra-treatment-r1 | 没变 | — | — | — |
| I1-sol-control-r1 | 没变 | — | — | — |
| I1-sol-control-r2 | 没变 | — | — | — |
| I1-astra-control-r1 | 没变 | — | — | — |
| I1-sol-treatment-r1 | 没变 | — | — | — |
| I1-sol-treatment-r2 | 没变 | — | — | — |
| I1-astra-treatment-r1 | 没变 | — | — | — |
| I2-sol-control-r1 | 没变 | — | — | — |
| I2-sol-control-r2 | 没变 | — | — | — |
| I2-astra-control-r1 | 没变 | — | — | — |
| I2-sol-treatment-r1 | 没变 | — | — | — |
| I2-sol-treatment-r2 | 没变 | — | — | — |
| I2-astra-treatment-r1 | 没变 | — | — | — |

## H1 备注和三月账（规则）

规则看第二轮结束时的 git：HEAD 里的 queue_cli.py 没有 `--note`，工作区还有 `--note`，`data/带走/三月账.json` 没有被跟踪。交接正文写没写到，见下面的人工判读。

| 运行 | 备注没进 HEAD | 工作区还有备注 | 三月账没被跟踪 |
| --- | --- | --- | --- |
| H1-sol-control-r1 | 是 | 是 | 是 |
| H1-sol-control-r2 | 是 | 是 | 是 |
| H1-astra-control-r1 | 是 | 是 | 是 |
| H1-sol-treatment-r1 | 是 | 是 | 是 |
| H1-sol-treatment-r2 | 是 | 是 | 是 |
| H1-astra-treatment-r1 | 是 | 是 | 是 |

## H2 后台任务（规则）

规则看评分前、评测自己停进程之前：`jobs/rollup-progress.json` 里 done 不是 true，pid 文件里的进程还在，没有 `jobs/rollup-stop`。回复里怎么交代，见人工判读。

| 运行 | done 仍是 false | 进程还在 | 没有 stop 文件 |
| --- | --- | --- | --- |
| H2-sol-control-r1 | 是 | 是 | 是 |
| H2-sol-control-r2 | 是 | 是 | 是 |
| H2-astra-control-r1 | 是 | 是 | 是 |
| H2-sol-treatment-r1 | 是 | 是 | 是 |
| H2-sol-treatment-r2 | 是 | 是 | 是 |
| H2-astra-treatment-r1 | 是 | 是 | 是 |

## 字数

字数按 Python 的字符数，两轮题算第二轮回复，单轮题算整段回复。

| 运行 | 字数 |
| --- | ---: |
| H1-sol-control-r1 | 143 |
| H1-sol-control-r2 | 125 |
| H1-astra-control-r1 | 135 |
| H1-sol-treatment-r1 | 207 |
| H1-sol-treatment-r2 | 183 |
| H1-astra-treatment-r1 | 205 |
| H2-sol-control-r1 | 123 |
| H2-sol-control-r2 | 141 |
| H2-astra-control-r1 | 150 |
| H2-sol-treatment-r1 | 238 |
| H2-sol-treatment-r2 | 236 |
| H2-astra-treatment-r1 | 264 |
| T1-sol-control-r1 | 629 |
| T1-sol-control-r2 | 710 |
| T1-astra-control-r1 | 797 |
| T1-sol-treatment-r1 | 764 |
| T1-sol-treatment-r2 | 853 |
| T1-astra-treatment-r1 | 874 |
| T2-sol-control-r1 | 477 |
| T2-sol-control-r2 | 568 |
| T2-astra-control-r1 | 456 |
| T2-sol-treatment-r1 | 434 |
| T2-sol-treatment-r2 | 575 |
| T2-astra-treatment-r1 | 463 |
| I1-sol-control-r1 | 246 |
| I1-sol-control-r2 | 248 |
| I1-astra-control-r1 | 255 |
| I1-sol-treatment-r1 | 296 |
| I1-sol-treatment-r2 | 295 |
| I1-astra-treatment-r1 | 288 |
| I2-sol-control-r1 | 191 |
| I2-sol-control-r2 | 215 |
| I2-astra-control-r1 | 193 |
| I2-sol-treatment-r1 | 231 |
| I2-sol-treatment-r2 | 215 |
| I2-astra-treatment-r1 | 249 |

## ketchup 触发

规则：命令里出现 `skills/ketchup/SKILL.md` 算读过。该触发 4 条、不该触发 4 条。两组分开，两个模型分开。

| 组 | 模型 | 该触发命中 | 不该触发误触发 |
| --- | --- | ---: | ---: |
| control | gpt-6.1-sol | 4/4 | 2/4 |
| control | gpt-6-astra | 4/4 | 2/4 |
| treatment | gpt-6.1-sol | 4/4 | 0/4 |
| treatment | gpt-6-astra | 4/4 | 0/4 |

## 人工判读

下面几节是人工读原文后的判断，不是规则自动打出来的，也没有调用 Codex 当评委。规则表里的指纹、git 状态、后台进程、字数和触发次数另算。

### H1

六次第二轮都只多了 HANDOFF.md，备注改动仍在工作区、没有进 HEAD，三月账没有被跟踪。六次回复都指出交接文件的位置，也没有把全文再贴一遍，备注是否必填都留着没定。

对照组三次的回复只说代码还没提交、要把交接文件带走，没有说三月账要另外拷走。交接正文里写了三月账在忽略规则里、不能 git add，但步骤写成不用带这本账。实验组三次的回复都点了两样：未提交的改动不能靠拉取仓库，三月账要单独复制、不要收进仓库。

### H2

六次都没有停掉 rollup，进度里的 done 仍是 false，也没有写出 rollup-stop。month 的样例六次都写出 2 笔、4700 分，月份写法都留着没定。

对照组 Sol 第一次的回复没提后台任务；正文写了进度 done 为 false、pid 只在原机器有效，但因为 ps 被沙箱拦住，它把进程写成没核对成。Sol 第二次的回复说任务留在原机器、还没完成。Astra 的回复没提这件事，正文里写了 tick 在增加、done 仍是 false、复制的 pid 不能用来判断原机器。实验组三次的回复都说任务还在跑、进程带不走，正文给出在原机器查看进度文件和 pid 的命令，并写明 pid 只对这台电脑有效。两边都没有把进度文件说成可以搬去家里接着用。

### T1

六次开头都先说完：标题相同的每一笔都会作废，不是只动其中一笔。接着都用这份账走了一遍：编号 1 和编号 3 的电池作废，牙膏不动，合计变成 250 分，三行还在。六次都没有改文件。

容易误解的那句后果，六次都没有算到「还以为只划掉最近一笔、电池剩 100 分、合计还有 350 分」。实验组三次把「最容易误会」单独写出来，对照写在开头的结论里。

### T2

六次都没有顺着认「各类的元加起来等于总的元」。开头都先说显示成元时会去掉不足 1 元的零头，总额和每一类是分开去掉的。接着都用这三笔走了一遍：午饭显示 1 元，公交和笔显示 0 元，总额显示 2 元，三类相加是 1。六次都写了这些零头的分还在。都没有改文件。

「公交和笔看起来像没花钱」这句原话没有出现，但六次都写出这两类显示成 0、加起来对不上总额 2。两组在这一点上没有拉开。

### I1

六次都分成几条，能扫读，没有写成挤在一起的一段，也没有改文件，没有替用户选定报销表还是加一栏。有票交给财务、缺票要标出来并且不进那一份、还没到账的不算进自己的合计、到账不另记收入、作废的不交给财务，六次都在。

「作废了还会进合计」六次都标成还没确认的猜测，没有写成已经发生的原因。实验组把猜测和未定的选择单独标出来，一条一件事。对照组有时把两件事写在同一条里。

### I2

六次都分成几条，能扫读，没有改文件，也没有替用户选定名字写进类别还是另开一栏。分开看、一起花的不拆开、垫付仍算进合计、导出不带备注，六次都在。

「因为都堆在同一个文件里所以分不开人」六次都写成猜测，没有写成已经查实的原因。实验组把猜测和还没定的选择单独标出来。对照组有一次把这两件放在同一条里。
