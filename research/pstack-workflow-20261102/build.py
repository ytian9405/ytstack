from pathlib import Path
import json

OUT = Path(__file__).parent
BASE = 'https://github.com/cursor/plugins/blob/main/pstack/'

def src(path):
    return BASE + path

skills = {}
def skill(name, role, trigger, steps, note='', kind='skill', path=None):
    skills[name] = dict(name=name, role=role, trigger=trigger, steps=steps,
                        note=note, kind=kind, url=src(path or f'skills/{name}/SKILL.md'))

skill('poteto-mode', '主入口与规则路由', '用户明确进入模式，或要求采用这套工作方式。',
      ['复述目标，读取原则索引。', '匹配 playbook，把原文步骤复制到待办；跳过项保留 skip 原因。', '在步骤中按条件调用技能，监督代理产物，核验后交付。'],
      '它由当前聊天负责执行；不是把整套 playbook 交给一个 poteto-agent。规则写在 Markdown 中，不是由代码强制运行的 DAG。')
skill('setup-pstack', '设置角色模型与预算', '首次配置，或更改模型与推理预算。', ['检测可用模型。', '选择预算及各角色的模型。', '写入持久规则，后续技能读取。'], '配置影响后续角色分配；不是每次任务的必经前置步骤。')
skill('poteto-help', '解释使用方法', '用户请求帮助或不知道如何选择技能。', ['明确问题。', '读对应技能或指南。', '给出说明、源码和可发送提示词。'], '帮助请求不会启动正式任务。')
skill('in-your-own-words', '复述用户意图', '用户单独要求复述；interrogate 也会显式调用。', ['用自己的话写出用户目标和真正要解决的问题。'], 'poteto-mode 首条消息有相同行为的内联指令，但未显式调用这个技能。不能把行为相似一律画成技能依赖。')
skill('sharpen', '深化任务提示词', '用户明确要求深化提示词。', ['补足专业做法、原始材料、方法工具、外部验证。', '重写提示词，保留用户选择。'], '产物是提示词；默认主干没有规定自动调用 sharpen。')
skill('how', '理解运行机制', '调查、非简单改动、架构判断。', ['简单问题用一个解释代理。', '复杂问题并行探索 2–4 个方向。', '解释代理核对源码，汇总概念、流程、位置、易错点。'], '它的探索者使用只读代理。')
skill('why', '追查历史原因', '动机问题、回归历史、既有设计原因。', ['先建立代码、提交、PR 的调查锚点。', '按可用来源并行调查。', '合并发现，区分证据、推断、猜测和未知。'], '为使用 MCP 会启用 agent 模式，但调查者不应修改数据；来源不可用要列为缺口。')
skill('teach', '把机制与动机讲懂', '用户请求教学式解释。', ['按问题范围调用 how 和 why，可以并行。', '组合成通俗解释，保留 why 的置信表述。', '先给最小完整解释，再按追问逐步展开图示。'], '这是可直接调用的组合技能，默认主干没有要求每次都 teach。')
skill('recall', '恢复跨会话上下文', '开始或恢复一个主题，需要找回近期工作。', ['锁定工作区、主题和时间范围。', '查聊天；具体功能还要借 why 的来源调查。', '核对分支、PR 和工单现状，给出摘要与下一步。'], '默认近期为七天。接手一条具体旧会话，应走 Session pickup playbook。')
skill('ketchup', '汇报当前会话的新变化', '用户主动要求；Autopilot 有变化的审计 tick 也会调用。', ['汇总用户上次消息后的工作。', '核对当前状态和证据。', '解释变化，列出全部待用户决定的事项。'], '这一轮只读。不是 recall 的跨会话检索；也不是每一步都自动播报。')
skill('ketchup-video', '用视频汇报变化', '用户要求视频形式的 ketchup。', ['遵循 ketchup 的调查范围和决策清单。', '用真实材料制作最多十页无声横屏视频。', '检查字幕、逐页画面和停留时间。'], '对 ketchup 的复用关系不意味着先生成一份重复文字汇报。')
skill('blast-radius', '检查改动的连带影响', '单独要求评估风险或检查小改动的隐性影响。', ['找出改动安全所依赖的关键事实。', '追踪时序、协议和下游行为。', '运行真实代码证明，分别报告风险和排除项。'], 'PR 模板有 Blast Radius 标题，但并不等于自动调用这个技能。')
skill('architect', '先设计数据和接口', '代码跨函数边界；Feature playbook 直接要求。', ['用 how 理解现有系统；改变所有权/分层时加 why。', '调用 arena，比较至少两种结构，选出统一设计。', '按草图实现；反复出现结构性摩擦时重新设计。'], '只有用户选择 checkpoint 时，才在设计后等待确认。')
skill('arena', '比较与融合多个候选', 'architect 的设计探索；实现存在多种有效结构；显式调用。', ['同一任务分给隔离的候选代理。', '按评分标准阅读与跨模型评判。', '选择基底、吸收其他方案的优点，最后验证。'], '评判在候选完成后启动；这与 swarm 的分片汇总不同。')
skill('swarm', '并行覆盖或竞赛', '需要分片验证、覆盖检查、竞赛或探索；Autopilot 独立验收。', ['声明完成标准、分片/竞赛形状和选择规则。', '并行启动独立工作者。', '核对 SHA、方法和证据，汇成一份报告。'], '缺失结果属于覆盖缺口，不能当作通过。')
skill('interrogate', '对抗式寻找可复现缺陷', '有争议的设计；明确要求审查改动。', ['调用 in-your-own-words 明确意图。', '复用 arena 的配置、隔离和并行启动步骤。', '各审查者运行复现；主代理重跑，保留确证缺陷。'], '只复用 arena 的部分阶段，跳过选基底和融合；本技能不应用修复。')
skill('tdd', '先得到失败证据再修复', '用户要求，或缺陷有明确且便宜的本地测试路径。', ['写最小回归测试。', '先运行并确认因目标缺陷失败。', '修复后重新运行，记录失败到成功。'], '昂贵、集成密集或不明确的测试路径可跳过；不能画成所有任务必经。')
skill('benchmark-checklist', '核查性能数字可信度', '运行基准或报告实际测量的性能变化。', ['明确要支持的性能结论。', '检查瓶颈、公平配置、错误、缓存和重复性。', '核验端到端意义并保留证据。'], 'Perf 的基线与后续数字都要检查；普通功能不自动跑基准。')
skill('no-comments', '审查注释和被掩盖的结构问题', '代码交付进入审查前。', ['调用 comment-sicko 审查范围内的注释。', '核验发现及保留例外。', '修正接受的问题，需要结构设计时调用 architect。'], 'comment-sicko 是代理角色，不是技能节点；必要时会触发实现修复和再次验证。')
skill('typescript-best-practices', 'TypeScript 类型规范', '读取或修改 TypeScript。', ['先应用 type-system-discipline。', '采用判别联合、语义类型和边界解析。', '避免不可信类型断言，穷尽变体。'], '语言条件触发，不是所有仓库的通用必经步骤。')
skill('figure-it-out', '为复杂单次任务设计流程', '大范围/跨模块改造、用户离开后审阅的复杂任务，或无现成流程。', ['定义可证伪的完成标准与范围。', '设计阶段、基线和验证工具。', '逐单元进行假设、修改、测量、保留或回退。', '通过 show-me-your-work 贯穿记录决策。'], '它设计并执行一次专门流程；多日项目编排则走 Orchestrate playbook。')
skill('show-me-your-work', '记录可审计决策', '长期、自主、多阶段任务，以及用户回来后审阅的工作。', ['维护一份 TSV。', '逐条记录选择、理由、证据和结果。', '按需要保留本地或提交为审计材料。'], '贯穿任务，不能只画在任务结束后。')
skill('create-verification-skill', '生成项目专属验收技能', '项目缺乏实际启动、操作和取证的验证方法。', ['调查启动、操作、观察和隔离方式。', '生成 verify-<app> 与首批功能地图。', '按产物跑通一个真实功能，取证、清理并确认材料保留。'], '不是所有工作自动调用的步骤。生成一次后，后续任务使用项目 verify 技能。')
skill('maintain-verification-skill', '维护已有验收技能', '功能和操作路径变化，验证地图可能过时。', ['逐功能源码调查。', '一次真实操作覆盖所有功能。', '只修改验收技能、地图及自有脚本。'], '产品回归要报告；不得为了通过而掩盖回归。')
skill('create-formal-verification-skill', '创建关键性质的验证', '并发、重试或状态机需要超出常规测试的检查。', ['选关键性质与合适工具。', '绑定模型和真实代码，保留界限与假设。', '注入坏变体证明检查能失败，再生成可复查技能。'], '结论只覆盖明示范围。TLA+ 的结果交给 statechart 展示。')
skill('maintain-formal-verification-skill', '同步形式验证与代码', '被覆盖的代码变化，而验证材料未同步。', ['追踪同步提交后的改动。', '依据代码更新模型和性质。', '重新运行并区分过时、真实缺陷和阻塞。'], '默认只改验证材料；不能降低性质以求通过。')
skill('statechart', '检查并展示状态路径', '需要用状态图解释 TLA+ 检查结果。', ['运行模型检查。', '生成用户能读懂的 Mermaid 状态图。', '给出每个违规状态的最短到达路径。'], '它是带脚本的具体技能；不代表所有 pstack 工作都经过形式验证。')
skill('unslop', '清理套路与空泛表达', 'poteto-mode 下所有文字输出。', ['按规则删除空话、模糊归因和生硬套路。', '使用具体机制、数据及自然语言。'], '横向写作约束；通常从写作时开始应用，不只在最后跑一次。')
skill('bro', '简明重述上一条回答', '用户要求把上一条说得更通俗。', ['保留意思，用自然、简明、少术语的语言重述。'], '无资料调查步骤。ketchup 复用它的语气，但不照搬“重述上一条”的任务。')
skill('technical-writing', '按读者目的组织技术写作', '文档、RFC、README、PR 及提交说明。', ['选择文档类型。', '应用技术写作、简明语言和消歧规则。', '应用 unslop。'], 'PR 和提交说明应用除 Diátaxis 外的层次；不是每条短回复都要完整执行。')
skill('automate-me', '生成个人工作模式', '用户希望固化或更新自己的工作方式。', ['提取当前工作区的工作习惯。', '借 create-skill 编写个人 -mode。', '用 unslop 整理指令。'], '这是建立个人入口的支线，不会在每个任务自动学习。')
skill('reflect', '复盘并提议更新技能', '用户明确要求任务复盘。', ['三个视角并行审查当前会话。', '综合为 Accepted / Rejected / Backlog。', '获得明确批准后修改获选的技能副本。'], '能用结构化机制约束的经验转入待办；技能修改必须先得到用户批准。')
skill('correct', '从结构上消除反复错误', '用户要求处理反复出现的错误。', ['从历史记录归纳至少重复发生的错误类。', '优先架构，再类型、lint/CI、测试，最后文字。', '用真实历史错误证明新约束有效。'], '与 reflect 的“改技能指令”不同，这里会实际改变仓库的约束。')
skill('make-bot-ui', '网页触发机器人', '要求搭建通过 webhook 唤醒 Grok Bot 的界面。', ['创建 webhook routine。', '服务端保管 sender key。', '实现按钮和服务端请求，按需通过 Tailscale 访问。'], '特定集成支线，不是核心开发流水线中的固定步骤。')
for name, role in [('deslop','提交前清理代码'),('control-ui','操作浏览器 / Electron / Web 界面'),('control-cli','操作 CLI / TUI')]:
    skill(name,role,'相关任务的提交或实际验收。',['从 cursor-team-kit 读取并执行该技能。'],'pstack 引用，但不在 pstack 的技能目录内。','external', '../cursor-team-kit')
skill('create-skill','创建或更新技能','编写 SKILL.md、个人模式或较大的技能修订。',['使用 Cursor 内置 authoring 能力。'],'Cursor 内置依赖；不是 pstack 自带技能。','external','skills/poteto-mode/playbooks/authoring-a-skill.md')
skill('verify-<app>','项目生成的真实验收','生成项目验证技能后，检查实际行为。',['按项目记录的启动、操作、取证和清理步骤执行。'],'这是占位命名约定，不是 pstack 内置技能；不是每个项目都已有。','external','skills/create-verification-skill/SKILL.md')
skill('setup-benny','配置独立的 Benny 自动化包','用户明确要求安装或配置 Benny。',['复制自动化包并配置项目范围的 pstack 依赖。','准备 Slack、工单、控制适配器与预算。','明确授权后配置两个在线自动化。'],'它不注册为普通斜杠技能；在目标仓库中直接读取。','automation','automations/benny/skills/setup-benny/SKILL.md')
skill('triage-issue-reports','分类和去重反馈','已配置的 Benny 自动化收到指定 Slack 新报告。',['读取报告和附件，按原因追踪归属。','工单去重，仅明确的新缺陷建单。','在原线程提交一次判定及可信标记。'],'此技能不复现或修复；后续自动化读取判定标记。','automation','automations/benny/skills/triage-issue-reports/SKILL.md')
skill('reproduce-and-fix-issues','复现和修复已确认反馈','Benny 复现自动化等待并读到可信 triage 标记。',['真实界面中复现两次并保留证据。','有既有修复则先验证；确认缺陷后尝试有界修复。','前后验证通过才开草稿 PR。'],'与普通 Opening a PR 的 ready 要求不同，此独立包只开草稿 PR，不合并部署。','automation','automations/benny/skills/reproduce-and-fix-issues/SKILL.md')

principles = [
('laziness-protocol','最小必要改动','删除重复决策，避免多余封装。','核心'),
('foundational-thinking','先设计基础结构','先确定数据形状、共享状态和基础设施。','核心'),
('redesign-from-first-principles','把新需求纳入整体设计','把新要求当作最初就有的条件，重新设计并逐步交付。','核心'),
('attack-the-premise','验证反复失败的共同前提','同一前提下两次修复失败，先直接检验该前提。','核心'),
('subtract-before-you-add','先减复杂度','删死代码、无效校验和多余引用，再增加能力。','核心'),
('minimize-reader-load','降低理解负担','减少跳转层数和必须记住的隐藏状态。','核心'),
('outcome-oriented-execution','围绕最终架构推进','计划内、可逆的迁移用明确阶段验证最终状态。','核心'),
('experience-first','使用体验优先','为最终用户和维护者改善核心工作流程。','核心'),
('exhaust-the-design-space','比较真实原型','新交互或关键架构先比较两三个候选。','核心'),
('build-the-lever','建立可重跑工具','用脚本、生成器、codemod 或验证工具替代大量手工。','核心'),
('model-the-domain','用结构表达业务','状态机、类型、表和适当的数据结构优先。','架构'),
('boundary-discipline','边界校验','在外部输入边界解析校验，内部用可信类型。','架构'),
('type-system-discipline','让类型排除非法状态','语义类型、穷尽变体，从权威结构推导类型。','架构'),
('make-operations-idempotent','让操作安全重跑','中断、重试和半成品下仍收敛到正确状态。','架构'),
('migrate-callers-then-delete-legacy-apis','迁移调用者并删除旧接口','适用于没有外部兼容要求的协调式内部迁移。','架构'),
('separate-before-serializing-shared-state','先隔离共享写入','独立文件、分支或状态；确需共享才用实际串行机制。','架构'),
('prove-it-works','检查真实产物','运行真实功能、读实际值，保留可复验的证据。','验证'),
('fix-root-causes','追到最初错误','先复现，用运行证据区分根因和症状。','验证'),
('sequence-verifiable-units','逐单元验证','每一步到达可验证状态，再推进下一步。','验证'),
('test-behavior-not-implementation','检查可观察行为','用户行为破坏时失败，内部重构时保持通过。','验证'),
('explain-the-number','解释测量数字','检查瓶颈、误差、缓存、错误和真正执行的工作。','验证'),
('guard-the-context-window','保护上下文','批量材料交子代理，主线程保留有证据的摘要。','协作'),
('never-block-on-the-human','可逆工作自主推进','合理决策后展示结果，不可逆动作保留确认。','协作'),
('encode-lessons-in-structure','把经验变成约束','能用 lint、脚本或类型执行的规则，优先程序化。','复盘')]
for name, title, desc, group in principles:
    skill('principle-'+name,title,'符合该原则的触发情境时，读取其完整文件。',[desc],'原则按情境贯穿任务；24 个原则不是按顺序执行的 24 步。','principle')

interest = 'in-your-own-words sharpen how why teach recall ketchup ketchup-video interrogate create-verification-skill unslop bro technical-writing reflect principle-redesign-from-first-principles'.split()

def S(name, note='', optional=False): return dict(skill=name,note=note,optional=optional)
def A(title,note=''): return dict(title=title,note=note,kind='action')
flows=[]
def flow(id,title,group,summary,steps,notes=(),path=None):
    flows.append(dict(id=id,title=title,group=group,summary=summary,steps=steps,notes=list(notes),url=src(path or f'skills/poteto-mode/playbooks/{id}.md')))

flow('investigation','只读调查','理解与诊断','调查直接交付答案。代码变更应重新路由。',
     [S('how'),S('why','动机问题才加',True),S('unslop'),A('交付调查答案','无 PR / 无 babysit')],
     ['源码明确禁止只读调查自动进入 PR、babysit 或 architect；需改代码时，交还用户并转 Bug fix 或 Feature。'])
flow('bug-fix','修复缺陷','开发与交付','先在真实使用路径复现，再定位、修复并在同一路径验收。',
     [S('control-ui','Web / Electron 表面',True),S('control-cli','CLI / TUI 表面',True),A('真实复现','选择匹配的操作技能'),S('how'),S('why','回归历史'),A('运行证据定位根因'),S('tdd','有便宜测试时；先红后绿',True),S('architect','跨函数边界',True),A('实现修复','poteto-agent 执行'),A('同一路径验收','原复现由失败变成功'),A('Opening a PR','见 PR 交付路径')],
     ['TDD 是贯穿修复的包围关系，图中节点表示先建立失败测试；修复后还要再运行。', 'control-ui 与 control-cli 按操作表面选择；原生移动端采用项目可用控制方法。'])
flow('feature','开发新功能','开发与交付','先理解，再比较结构，最后实现、验收和准备 PR。',
     [S('how'),S('architect'),S('arena','architect 内部的设计比较'),A('分解实现任务','明确数据形状和成功条件'),S('arena','多种实现结构时替代单代理',True),A('实现并真实验收'),S('interrogate','设计存在争议',True),A('Opening a PR','见 PR 交付路径')],
     ['architect 已含 arena，不要理解为两个独立设计竞赛。第二个 arena 是实现存在多种有效结构时的实现竞赛。', '实现阶段的 arena 替代单个编码代理；它不是在全部实现结束后再补跑一次。'])
flow('refactoring','行为保持的重构','开发与交付','先固定当前行为，再逐步改变结构并证明等价。',
     [S('how'),A('固定行为基线','特征测试 / 快照 / 等价工具'),S('principle-redesign-from-first-principles'),S('architect','跨函数边界',True),S('principle-subtract-before-you-add'),A('逐步迁移','每一步保住基线'),S('principle-prove-it-works'),A('Opening a PR')],
     ['新功能或缺陷修复应拆出去。大范围、跨模块重构转 figure-it-out。'])
flow('prototype','原型与方案决策','理解与诊断','通过最小可运行原型消除可实验判断的不确定性。',
     [A('限定要决定的问题'),S('principle-exhaust-the-design-space','有候选方案时'),A('隔离目录制作原型'),S('control-ui','可视原型操作与截图',True),A('观察结果并比较'),A('交付决策与临时产物','选定方向再转 Feature / architect')],
     ['原型是可丢弃产物，不是生产代码；行为/时序问题可以用最小脚本直接观察。'])
flow('perf-issue','一次性能修复','理解与诊断','真实基线 → 有依据的改动 → 真实复测。',
     [A('采集基线 trace','使用匹配的控制技能'),S('benchmark-checklist'),S('how'),S('architect','跨函数边界',True),A('实现并重新采样'),S('benchmark-checklist','再次核验数字'),A('比较测量产物'),A('Opening a PR')],
     ['编译、截图或代理报告不能替代性能测量；实际基线和复测要可比。'])
flow('hillclimb','持续指标优化','长期与多 PR','冻结可信测量方法，用逐轮实验追求目标。',
     [S('how'),S('principle-build-the-lever'),S('benchmark-checklist'),S('show-me-your-work'),A('提出单一假设'),A('最小修改与测量','有效则保留，无效则回退'),S('benchmark-checklist','每个数字的可信度'),A('未到目标则回到假设','逐个保留有效提交'),A('Opening a PR')],
     ['这是一条循环。达到目标或剩余收益不值得成本时退出；不能降低目标冒充完成。'])
flow('runtime-forensics','运行时取证','理解与诊断','从活进程采集信号，证明机制，交付诊断。',
     [A('匹配表面采集信号'),S('principle-guard-the-context-window'),A('定位热点 / 保留链'),A('插桩证实机制'),A('映射到源码'),S('unslop'),A('交付诊断','需修复则转 Bug fix / Perf')],
     ['默认交付诊断，不自动修复。'])
flow('trace-forensics','已有 trace 取证','理解与诊断','把已有性能文件变成可查询证据，再定位原因。',
     [S('principle-guard-the-context-window'),A('解析并转为可查询数据'),A('定位热点 / 泄漏链'),A('映射到源码'),A('有成对采样则比较'),S('unslop'),A('交付诊断','需修复则转 Bug fix / Perf')],
     ['没有成对捕获时，按产物能支持的最强假设报告，不冒充已证实根因。'])
flow('visual-parity','像素一致性迁移','开发与交付','先保存视觉基线，再逐组件迁移和比较。',
     [A('建立视觉基线'),S('principle-separate-before-serializing-shared-state'),A('逐组件迁移'),S('control-ui'),A('像素差异检查','非零差异回到迁移'),A('Opening a PR')],
     ['不得修改测试或篡改基线来通过比较；共享基础组件先迁移。'])
flow('authoring-a-skill','编写或修改技能','技能与评估','用内置 authoring 能力编写，并验证结构与引用。',
     [S('create-skill'),A('验证元数据与引用'),A('结构性测试','主观规则可跳过'),A('Opening a PR')])
flow('eval','评估技能与提示词','技能与评估','候选与裁判隔离，尽量不让候选知道被测目标。',
     [A('定义评分标准','仅裁判可见'),A('隔离候选环境'),S('arena','只复用并行候选与盲评阶段'),A('检查完整执行记录'),A('交付评估与证据')],
     ['这是评估协议，不是照搬完整 arena；候选不应看到模型标签和测试意图。'])
flow('babysit','把 PR 推到可合并状态','PR 与运行控制','用户明确要求后才开始；修评审和检查，但合并另走 Shipping。',
     [A('声明工作模式','check / drive / background / threads-only'),A('检查最低未合并 PR'),A('处理评审与检查','冲突需报告 owning branch'),S('no-comments','涉及修复后审查',True),A('核对 forge 的可合并状态'),S('unslop'),A('报告 merge-ready','并不代表已经合并')],
     ['普通情况下开 PR 不启动 babysit。Autopilot owner 的任务书可显式包含该循环。'])
flow('shipping','独立验证后合并','PR 与运行控制','独立验证覆盖实际补丁，只合并从栈底连续通过的部分。',
     [A('每 PR 一个独立验证者','不能是原作者'),S('control-ui','或匹配的控制技能',True),S('principle-prove-it-works'),A('核对补丁与当前 head'),A('从栈底逐个合并','只到连续验证通过的上限'),A('读回合并结果'),S('unslop')],
     ['Shipping 本身没有规定必须调用 swarm；Autopilot 的独立验收则显式使用 swarm。', '用户、平台和项目原有批准门槛仍然有效；图示不构成合并授权。'])
flow('autonomous-run','单任务自主循环','长期与多 PR','围绕明确的完成条件反复执行、验证和记录。',
     [A('定义可证伪完成条件'),S('show-me-your-work'),A('路由到具体任务流程'),A('观察、修改、验证'),A('未达条件则继续','Cursor /loop 是运行控制'),S('unslop'),A('交付最终状态')],
     ['show-me-your-work 贯穿每轮；平台 /loop 不是一个 pstack 技能。'])
flow('orchestrate','长期项目编排','长期与多 PR','协调者负责拆解、派工和验收，多日程序由多批工作者完成。',
     [A('项目协调与工作队列'),S('show-me-your-work'),A('新工作者执行匹配流程','poteto-agent 是角色'),A('不同模型的独立验证者','每 PR 一个，非原作者'),A('检查真实进展与产物'),A('继续派工 / 替换阻塞者'),S('unslop'),A('报告项目与 PR 状态')],
     ['一项会话内可完成的工作不应因措辞宏大就升级为项目程序。此图仅展示技能接口，协调规则仍由 playbook 负责。'])
flow('autopilot-full','多 PR 自主完成并合并','长期与多 PR','每 PR 一个 owner；根协调者的独立验收与作者自证分离。',
     [A('明确队列与用户门槛'),S('show-me-your-work'),A('各 owner 实现与自证'),S('deslop'),S('no-comments'),S('swarm','代码 ready head 的独立验收'),A('CI / babysit / 准备合并'),A('owner 合并已验证补丁'),S('ketchup','有变化的审计 tick'),A('继续审计至队列完成')],
     ['完整 swarm 在代码 ready 时执行；较小修改有更轻的复验规则，不是每次修改都重跑全部 swarm。', '用户门槛优先；放宽检查需要独立证明和根协调者复核。'])
flow('autopilot-stack','多 PR 构建至已验证','长期与多 PR','复用 Autopilot-full，交给用户合并。',
     [A('明确 PR 依赖'),S('show-me-your-work'),A('owner 实现与自证'),S('deslop'),S('no-comments'),S('swarm'),A('CI / babysit / 最终复核'),S('ketchup'),A('交付已验证 PR','到此停止，不合并')],
     ['只有依赖别的 PR 时才堆叠；用户接手后，没有新的 go 不再 push。'])
flow('session-pickup','接手一个旧会话','PR 与运行控制','先重建具体会话状态，再把剩余任务交给匹配流程。',
     [A('读取原会话 / 分支'),A('重建完成与未完成状态'),A('选择剩余任务 playbook'),S('principle-prove-it-works'),A('继续原任务')],
     ['与 recall 的跨会话主题检索不同。不要无故重做已完成工作，同时要核验真实产物。'])
flow('pause-safely','安全暂停','PR 与运行控制','停止新任务，固化当前状态，并留下恢复入口。',
     [A('停止于安全边界'),A('保存未提交工作'),S('show-me-your-work','若已有记录则引用',True),A('写恢复说明'),A('暂停并交付恢复点')],
     ['暂停不是完成；不因暂停额外开 PR 或 push。'])
flow('multi-phase-plan','多阶段计划','长期与多 PR','计划是产物；执行需要用户明确 go。',
     [A('用原型回答可实验问题'),A('探索并确定 PR 依赖'),S('technical-writing'),S('unslop'),A('运行 check-plan.mjs'),A('交付计划并暂停','明确 go 后进 Autopilot / Orchestrate')],
     ['计划还声明每个 PR 的真实验证与性能门槛；计划声明不是验证已通过。'])
flow('worktree-cleanup','工作区与模拟器清理','PR 与运行控制','先审计活跃使用与未保存状态，再清理确认可删除的对象。',
     [S('principle-build-the-lever'),A('审计路径和使用状态'),S('principle-prove-it-works'),A('未提交或在用则暂停'),A('清理确认集合'),A('验证空间与剩余对象')],
     ['这是磁盘清理 playbook，不是普通开发中每次自动执行的末尾步骤。'])
flow('opening-a-pr','PR 交付通道','开发与交付','代码清理、注释审查和提交/PR 文字各有不同技能。',
     [S('deslop','每次提交前'),S('technical-writing','提交说明及 PR 文字'),S('unslop','写作同时应用'),S('no-comments','审查前'),A('创建 ready PR','读回真实状态'),A('继续构建 / 汇报 URL','需另行请求 babysit')],
     ['这些是各生命周期点的门槛，不是强制的单次串行顺序；no-comments 产生修改后仍需验证和清理。', 'main 文档说所有 playbook 结尾走 Opening a PR，但只读调查、取证、原型、暂停、计划等叶文件有更具体的结束规则。本图展示这些例外。'])

extra = []
def extra_flow(id,title,summary,steps,notes=(),path=None):
    extra.append(dict(id=id,title=title,group='技能组合',summary=summary,steps=steps,notes=list(notes),url=src(path or f'skills/{id}/SKILL.md')))
extra_flow('teach','教学：how 与 why','按范围真实调用两种调查，再组合解释。',[S('teach'),S('how','运行机制'),S('why','历史动机；可与 how 并行'),S('unslop'),A('分层讲解与图示')],['系统性问题可以并行调用 how 与 why；较小问题按需要缩小范围。'])
extra_flow('recall','恢复上下文','聊天历史、共享记录和真实状态三者交叉确认。',[S('recall'),A('按主题检索本地聊天'),S('why','具体功能的共享记录调查',True),A('核验当前分支 / PR / 工单'),S('unslop'),A('摘要、问题与下一步')])
extra_flow('ketchup-video','视频汇报','复用汇报契约，视频替代文字进展摘要。',[S('ketchup-video'),S('ketchup','复用调查范围与决策清单'),S('bro','只复用通俗语气'),A('真实材料制作与检查视频'),A('视频 + 用户决策事项')],['此处箭头主要表示行为复用，不是先生成三份成品。'])
extra_flow('interrogate','对抗式审查','审查者的主张必须能被主代理重新运行证明。',[S('interrogate'),S('in-your-own-words'),S('arena','只复用配置、隔离、fan-out'),A('各代理实际运行复现'),S('principle-prove-it-works'),A('合并已验证发现','不应用修复')])
extra_flow('create-verification-skill','建立验证体系','生成器、生成的技能、维护器是三种不同角色。',[S('create-verification-skill'),S('verify-<app>','按生成步骤跑通真实功能'),A('后续任务复用 verify 技能'),S('maintain-verification-skill','功能变化后',True)],['维护验证技能不是修复产品；发现产品回归要另外报告。'])
extra_flow('create-formal-verification-skill','关键性质验证','在明确范围内验证关键性质，并维护模型与代码对应。',[S('create-formal-verification-skill'),S('statechart','采用 TLA+ 时',True),A('生成可重跑的项目技能'),S('maintain-formal-verification-skill','覆盖代码变化后',True)],['这里不代表整个系统被证明正确，范围、假设和界限要单独记录。'])
extra_flow('reflect','复盘改进技能','三视角复盘、综合筛选、结构化分流、批准后编辑。',[S('reflect'),A('三视角并行审查','判断 / 工具 / 发散'),S('principle-encode-lessons-in-structure'),A('展示建议并等待批准'),S('create-skill','较大的获批技能修改',True),A('修改技能副本'),A('验证并汇报')],['小修可直接编辑；可用脚本/lint约束的经验转入待办。原版还包含写团队待办的动作，使用时受当前权限约束。'])
extra_flow('automate-me','形成个人模式','从自己的工作习惯形成一个可调用入口。',[S('automate-me'),A('提取工作习惯'),S('create-skill'),S('unslop'),A('个人 -mode 技能')])
extra_flow('correct','消除反复错误','把重复纠正落实到仓库结构与自动检查。',[S('correct'),A('归纳重复错误'),A('架构 → 类型 → lint/CI → 测试'),S('principle-encode-lessons-in-structure'),A('用历史错误证明检查有效')])
extra_flow('benny','Benny 独立自动化','这组内部技能由两个事件自动化驱动，不经过普通 poteto-mode 路由。',[S('setup-benny'),A('报告事件触发两个自动化'),S('triage-issue-reports'),A('可信判定标记','复现自动化等待这个契约'),S('reproduce-and-fix-issues'),A('草稿 PR 或验证结论','不合并、不部署')],['两个自动化都由配置的事件触发。这里的先后表示判定标记的数据依赖，不是一个主代理按顺序执行全部技能。'],path='automations/benny/FOR_AGENTS.md')
extra[0]['diagram'] = dict(nodes=[
    dict(key='teach',skill='teach',x=24,y=180),
    dict(key='how',skill='how',x=299,y=40,note='运行机制 · 并行分支'),
    dict(key='why',skill='why',x=299,y=320,note='历史动机 · 按问题范围'),
    dict(key='unslop',skill='unslop',x=574,y=180,note='合并成通俗解释时应用'),
    dict(key='answer',title='逐层讲解与图示',kind='action',x=849,y=180,note='根据读者追问继续展开')],
    edges=[dict(a=a,b=b,label=l,type='solid',axis='horizontal') for a,b,l in [('teach','how','调查'),('teach','why','调查'),('how','unslop','汇合解释'),('why','unslop','保留置信表述'),('unslop','answer','交付')]],height=470)

overview_nodes = [
dict(key='setup',skill='setup-pstack',x=24,y=28,note='一次性 / 按需配置',optional=True),
dict(key='mode',skill='poteto-mode',x=435,y=28,note='复述目标 · 读取原则 · 路由'),
dict(key='invest',title='只读调查流程',kind='action',x=24,y=195,note='Investigation'),
dict(key='build',title='开发 / 重构流程',kind='action',x=299,y=195,note='代码变更与实际验收'),
dict(key='custom',title='复杂单次任务',kind='action',x=574,y=195,note='定制流程'),
dict(key='program',title='多 PR 项目流程',kind='action',x=849,y=195,note='Orchestrate / Autopilot'),
dict(key='h1',skill='how',x=24,y=365,note='运行机制'),
dict(key='h2',skill='how',x=299,y=365,note='理解受影响系统'),
dict(key='fig',skill='figure-it-out',x=574,y=365,note='设计可验证的阶段'),
dict(key='swarm',skill='swarm',x=849,y=365,note='Autopilot 独立验收'),
dict(key='why',skill='why',x=24,y=535,note='动机 / 历史问题时',optional=True),
dict(key='arch',skill='architect',x=299,y=535,note='Feature 必须 / 跨边界时'),
dict(key='log',skill='show-me-your-work',x=574,y=535,note='决策记录贯穿执行'),
dict(key='catch',skill='ketchup',x=849,y=535,note='Autopilot 审计有变化时',optional=True),
dict(key='clean',skill='unslop',x=24,y=705,note='交付调查答案'),
dict(key='arena',skill='arena',x=299,y=705,note='architect 内部比较候选'),
dict(key='proof',skill='principle-prove-it-works',x=574,y=705,note='每单元检查真实产物'),
dict(key='loop',title='继续 / 验证 / 合并',kind='action',x=849,y=705,note='取决于授权与具体流程')]
overview_edges = [
('setup','mode','读取模型配置','conditional'),
('mode','invest','路由','solid'),('mode','build','路由','solid'),('mode','custom','路由','solid'),('mode','program','路由','solid'),
('invest','h1','','solid'),('h1','why','涉及原因','conditional'),('why','clean','答案写作','conditional'),
('build','h2','','solid'),('h2','arch','开发条件','conditional'),('arch','arena','技能内部调用','solid'),
('custom','fig','','solid'),('fig','log','贯穿记录','solid'),('log','proof','逐单元验证','solid'),
('program','swarm','独立验证阶段','conditional'),('swarm','catch','审计有变化','conditional'),('catch','loop','后续运行控制','conditional')]

DATA=dict(version='0.15.36',checked='2026-11-02',skills=skills,flows=flows,extra=extra,interest=interest,
          principles=[dict(name='principle-'+n,title=t,desc=d,group=g) for n,t,d,g in principles],
          overview=dict(nodes=overview_nodes,edges=[dict(a=a,b=b,label=l,type=t) for a,b,l,t in overview_edges]))

CSS = r'''
:root{--bg:#f3f5f5;--paper:#fff;--ink:#142c36;--muted:#5b707b;--line:#dce4e7;--teal:#087f80;--purple:#7656ae;--orange:#b66b19;--blue:#2368ae}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif;font-size:14px;line-height:1.65}button,a{touch-action:manipulation}button{font:inherit}a{color:#12697e;text-decoration-thickness:1px;text-underline-offset:3px}header{padding:35px 4vw 20px;background:#142c36;color:#f5faf9}.eyebrow{font-size:11px;letter-spacing:2.5px;color:#99d5cf}h1{font-size:clamp(25px,3vw,38px);line-height:1.25;margin:10px 0 13px;font-weight:650}header p{max-width:1050px;color:#bcd0d6;margin:0 0 18px}.meta{display:flex;flex-wrap:wrap;gap:8px}.meta span{border:1px solid #3a515b;border-radius:5px;padding:3px 10px;font-size:12px}nav{display:flex;gap:6px;flex-wrap:wrap;padding:15px 4vw;background:#fff;border-bottom:1px solid var(--line)}button{cursor:pointer;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink);padding:8px 13px}button:hover{border-color:var(--teal);background:#f1fafa}button.active{background:var(--teal);color:white;border-color:var(--teal)}.layout{display:grid;grid-template-columns:215px minmax(0,1fr) 310px;gap:18px;padding:22px 3vw;max-width:1820px;margin:auto}.panel{background:white;border:1px solid var(--line);border-radius:9px;overflow:hidden}.sidebar{padding:14px;align-self:start;position:sticky;top:15px;max-height:88vh;overflow:auto}.sidebar h3{font-size:11px;letter-spacing:1px;color:var(--muted);margin:17px 0 5px}.sidebar button{display:block;width:100%;text-align:left;font-size:12px;margin-bottom:4px;border-color:transparent;padding:6px 9px}.sidebar button.active{background:#e0f2ef;color:#0c6265}.content{min-width:0}.intro{padding:22px 24px 8px}.intro h2{font-size:23px;margin:0 0 8px}.intro p{color:var(--muted);margin:0 0 10px}.intro .small{font-size:12px}.toolbar{padding:8px 24px 13px;display:flex;gap:9px;align-items:center;flex-wrap:wrap}.legend{font-size:11px;display:flex;gap:13px;flex-wrap:wrap;color:var(--muted)}.dot{width:8px;height:8px;border-radius:2px;display:inline-block;margin-right:4px}.graph{overflow:auto;padding:0 12px 10px}.graph svg{width:100%;min-width:760px;height:auto;display:block}svg text{font-family:"Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif}.graph .node{cursor:pointer;outline:none}.graph .node:focus rect,.graph .node:hover rect{stroke-width:3}.graph .node.selected rect{stroke:#173b48;stroke-width:3}.notes{margin:0 24px 22px;padding:13px 16px;background:#f4f7f8;border-radius:6px;font-size:12px}.notes p{margin:3px 0 8px}.notes p:last-child{margin:0}.detail{padding:20px;position:sticky;top:15px;align-self:start;max-height:88vh;overflow:auto;overflow-wrap:anywhere}.detail .tag{font-size:11px;color:var(--teal);letter-spacing:1px}.detail h2{font-size:19px;line-height:1.4;margin:10px 0}.detail h3{font-size:12px;color:var(--muted);margin-top:20px}.detail p{font-size:13px}.detail ol{padding-left:20px;font-size:13px}.detail li{margin-bottom:8px}.detail .source{display:block;border-top:1px solid var(--line);padding-top:14px;font-size:12px}.badges{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}.badges span{background:#f0f3f5;border-radius:4px;padding:2px 7px;font-size:11px}.catalog{padding:12px 24px 25px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.skillcard{text-align:left;padding:15px;line-height:1.6;min-width:0;overflow-wrap:anywhere}.skillcard strong{display:block;font-size:13px}.skillcard span{display:block;font-size:12px;color:var(--muted);margin-top:5px}.skillcard.interested{border-left:3px solid var(--teal)}.filter{width:100%;border:1px solid var(--line);padding:9px;border-radius:5px;margin:8px 0}.empty{padding:20px;color:var(--muted)}.foot{padding:0 4vw 25px;color:var(--muted);font-size:12px;max-width:1600px;margin:auto}.notice{border-left:3px solid #7a9dba;padding-left:12px}.tabs-note{font-size:11px;color:var(--muted)}#mobileMenu{display:none}.footer-links{display:flex;gap:16px;flex-wrap:wrap}.graph .edge{fill:none;stroke:#92a5ad;stroke-width:1.6}.graph .edge.conditional{stroke-dasharray:5 5}.graph .edgeLabel{font-size:10px;fill:#526a76;paint-order:stroke;stroke:#fff;stroke-width:5px;stroke-linejoin:round}.focus-only .node:not(.interested):not(.selected){opacity:.35}.focus-only .edge{opacity:.35}button:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid #edb956;outline-offset:3px}@media(min-width:1600px){.layout{grid-template-columns:235px minmax(0,1fr) 335px}}@media(max-width:1200px){.layout{grid-template-columns:180px minmax(0,1fr)}.detail{position:static;max-height:none;grid-column:2}.sidebar{grid-row:1/3}.graph svg{min-width:760px}}@media(max-width:750px){header{padding:25px 20px 17px}nav{padding:12px 20px}.layout{display:block;padding:15px}.sidebar{display:none}#mobileMenu{display:block;width:100%;padding:10px;margin-bottom:12px;background:white;border:1px solid var(--line);border-radius:6px}.detail{margin-top:15px}.intro{padding:18px}.toolbar{padding:8px 18px}.catalog{grid-template-columns:1fr;padding:10px 18px}.notes{margin:0 18px 18px}.foot{padding:0 20px 25px}}@media print{header{background:#fff;color:#142c36}.sidebar,nav,.toolbar,.detail,#mobileMenu{display:none}.layout{display:block;padding:0}.graph svg{min-width:0}.panel{border:0}.meta span{border-color:#ddd}header p{color:#415965}.foot{display:none}}
'''

JS = r'''
const D=JSON.parse(document.getElementById('data').textContent);
const $=s=>document.querySelector(s);
let mode='overview', selectedFlow='feature', selectedSkill='poteto-mode', focus=false, query='';
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors={skill:['#e7f4f1','#087f80'],principle:['#f0ebf8','#7656ae'],external:['#fff2df','#b66b19'],automation:['#e8f0fa','#2368ae'],action:['#f1f4f6','#899ea8']};
function wrap(s,max){let lines=[];while(s.length>max){let at=s.lastIndexOf('-',max);if(at<max*.35)at=max;else at++;lines.push(s.slice(0,at));s=s.slice(at)}if(s)lines.push(s);return lines}
function nodeSVG(n){const sk=D.skills[n.skill],kind=sk?.kind||n.kind||'action',title=sk?.name||n.title,c=colors[kind],key=n.key,interested=D.interest.includes(n.skill),chosen=n.skill===selectedSkill;let ls=wrap(title,title.length>25?24:25);if(ls.length>2)ls=[ls[0],ls.slice(1).join('')];const fs=title.length>25?13:15;let y=ls.length>1?33:42;return `<g class="node ${interested?'interested':''} ${chosen?'selected':''}" transform="translate(${n.x},${n.y})" data-skill="${E(n.skill||'')}" data-key="${E(key)}" role="button" tabindex="0" aria-label="${E(title)}"><title>${E(sk?.role||n.note||title)}</title><rect width="224" height="106" rx="7" fill="${c[0]}" stroke="${c[1]}" stroke-width="1.2" ${n.optional?'stroke-dasharray="5 4"':''}/><text x="15" y="16" fill="${c[1]}" font-size="9">${kind==='action'?'流程 / 动作':kind==='external'?'外部或项目技能':kind==='automation'?'自动化内部技能':kind==='principle'?'原则技能':'技能'}${n.optional?' · 按条件':''}</text>${ls.map((l,i)=>`<text x="15" y="${y+i*18}" font-size="${fs}" fill="#153642" font-weight="600">${E(l)}</text>`).join('')}<text x="15" y="87" font-size="10" fill="#4e6773">${E(n.note||sk?.role||'')}</text>${interested?'<circle cx="210" cy="15" r="3" fill="#087f80"/>':''}</g>`}
function edgeSVG(e,lookup){const a=lookup[e.a],b=lookup[e.b];if(!a||!b)return '';let path='',tx,ty;
if(e.axis==='horizontal'){let x1=a.x+224,y1=a.y+53,x2=b.x,y2=b.y+53,mid=(x1+x2)/2;path=`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`;tx=mid;ty=(y1+y2)/2-8}
else if(a.y===b.y){const dir=b.x>a.x?1:-1;let x1=a.x+(dir===1?224:0),x2=b.x+(dir===1?0:224),y=a.y+53;path=`M${x1},${y} L${x2},${y}`;tx=(x1+x2)/2;ty=y-9}
else{let x1=a.x+112,y1=a.y+106,x2=b.x+112,y2=b.y;const mid=(y1+y2)/2;path=`M${x1},${y1} C${x1},${mid} ${x2},${mid} ${x2},${y2}`;tx=(x1+x2)/2;ty=mid-8}
return `<g><path d="${path}" class="edge ${e.type==='conditional'?'conditional':''}" marker-end="url(#arrow)"/><text x="${tx}" y="${ty}" text-anchor="middle" class="edgeLabel">${E(e.label||'')}</text></g>`}
function svgGraph(nodes,edges,height){let map=Object.fromEntries(nodes.map(n=>[n.key,n]));return `<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="${height}" viewBox="0 0 1100 ${height}" aria-label="pstack 技能工作流" role="img"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#92a5ad"/></marker></defs>${edges.map(e=>edgeSVG(e,map)).join('')}${nodes.map(nodeSVG).join('')}</svg>`}
function timeline(f){if(f.diagram)return svgGraph(f.diagram.nodes,f.diagram.edges,f.diagram.height);const nodes=f.steps.map((s,i)=>{let r=Math.floor(i/4),c=i%4;if(r%2)c=3-c;return {...s,key:'s'+i,x:24+c*275,y:24+r*175}});const edges=nodes.slice(1).map((n,i)=>({a:nodes[i].key,b:n.key,label:'',type:n.optional?'conditional':'solid'}));return svgGraph(nodes,edges,Math.ceil(nodes.length/4)*175+10)}
function showDetail(name){if(!D.skills[name])return;selectedSkill=name;const s=D.skills[name];$('#detail').innerHTML=`<div class="tag">${s.kind==='principle'?'原则层':s.kind==='external'?'外部 / 项目依赖':s.kind==='automation'?'Benny 自动化技能':'技能节点'}${D.interest.includes(name)?' · 你关注的技能':''}</div><h2>${E(s.name)}</h2><p>${E(s.role)}</p><h3>何时触发</h3><p>${E(s.trigger)}</p><h3>源码里的执行逻辑</h3><ol>${s.steps.map(v=>`<li>${E(v)}</li>`).join('')}</ol><h3>需要分清的边界</h3><p>${E(s.note)}</p><a class="source" href="${E(s.url)}" target="_blank" rel="noopener">查看 GitHub 源文件 ↗</a><div class="badges">${D.flows.filter(f=>f.steps.some(n=>n.skill===name)).map(f=>`<span>${E(f.title)}</span>`).join('')}</div>`;document.querySelectorAll('.node').forEach(n=>n.classList.toggle('selected',n.dataset.skill===name));}
function navigation(){let html='';if(mode==='overview'){html='<h3>阅读顺序</h3><button data-mode="overview" class="active">01 总体路由</button><button data-mode="flows">02 任务路径</button><button data-mode="interest">03 你关注的技能</button><button data-mode="principles">04 横向原则</button><button data-mode="catalog">05 全部技能</button><h3>关键区别</h3><p class="tabs-note">技能是可调用单元。<br>Playbook 决定步骤。<br>原则在条件满足时约束决策。<br>代理是执行角色。</p>'}
else if(mode==='flows'){for(const group of [...new Set(D.flows.map(f=>f.group))]){html+=`<h3>${E(group)}</h3>`+D.flows.filter(f=>f.group===group).map(f=>`<button data-flow="${f.id}" class="${selectedFlow===f.id?'active':''}">${E(f.title)}</button>`).join('')}}
else if(mode==='interest'){html='<h3>技能组合与支线</h3>'+D.extra.map(f=>`<button data-extra="${f.id}" class="${selectedFlow==='x:'+f.id?'active':''}">${E(f.title)}</button>`).join('')+'<h3>你选的 15 个技能</h3>'+D.interest.map(n=>`<button data-skill="${E(n)}">${E(n.replace('principle-',''))}</button>`).join('')}
else{html='<h3>筛选技能</h3><input class="filter" aria-label="搜索技能" placeholder="搜索名称或用途" value="'+E(query)+'" id="search"><p class="tabs-note">点击卡片查看触发条件、执行步骤和源文件。原则卡片没有先后顺序。</p>'}
$('#sidebar').innerHTML=html;const opts=mode==='flows'?D.flows:mode==='interest'?D.extra:[];$('#mobileMenu').innerHTML=opts.map(f=>`<option value="${mode==='interest'?'x:':''}${f.id}" ${selectedFlow===(mode==='interest'?'x:':'')+f.id?'selected':''}>${E(f.title)}</option>`).join('');$('#mobileMenu').style.display=window.innerWidth<=750&&opts.length?'block':'none';
document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));}
function notesHTML(notes){return `<div class="notes">${notes.map(n=>`<p>${E(n)}</p>`).join('')}</div>`}
function render(){navigation();let html='';const legend=`<div class="legend"><span><i class="dot" style="background:#087f80"></i>工具技能</span><span><i class="dot" style="background:#7656ae"></i>原则技能</span><span><i class="dot" style="background:#b66b19"></i>外部 / 项目技能</span><span><i class="dot" style="background:#899ea8"></i>流程或动作</span><span>虚线 = 条件触发</span></div>`;
if(mode==='overview'){html=`<div class="intro"><h2>一套入口，按任务分流</h2><p>四类分支展示关键技能关系。切换「任务路径」可读全部 23 个 playbook 的具体步骤。</p><p class="small">图上的灰色框是流程 / 动作，其余框的单位都是技能。分支不是依次全部运行。</p></div><div class="toolbar">${legend}</div><div class="graph">${svgGraph(D.overview.nodes,D.overview.edges,835)}</div>${notesHTML(['poteto-mode 是规则驱动的入口；playbook 指定先后步骤，技能还会按事件插入。没有一条对所有任务相同的固定流水线。','图中从模式到分支的连线表示路由；从 architect 到 arena 表示内部调用。部分流程行动为方便理解而保留为灰色框。','只读调查可以没有 why；虚线技能不适用时跳过。程序分支以 Autopilot 的独立验收与汇报为例。'])}`;}
else if(mode==='flows'||(mode==='interest'&&selectedFlow.startsWith('x:'))){const f=mode==='flows'?D.flows.find(f=>f.id===selectedFlow):D.extra.find(f=>f.id===selectedFlow.slice(2));if(!f){selectedFlow=mode==='flows'?'feature':'x:teach';return render()}if(!f.steps.some(s=>s.skill===selectedSkill))selectedSkill=f.steps.find(s=>s.skill)?.skill||'poteto-mode';html=`<div class="intro"><h2>${E(f.title)}</h2><p>${E(f.summary)}</p><p class="small"><a href="${E(f.url)}" target="_blank" rel="noopener">该路径的源码 ↗</a> · ${f.diagram?'按箭头阅读并行分支与汇合。':'路径按蛇形阅读：第一行从左到右，第二行从右到左。'}</p></div><div class="toolbar">${legend}<button id="focus">${focus?'显示全部节点':'突出你关注的 15 项'}</button></div><div class="graph ${focus?'focus-only':''}">${timeline(f)}</div>${notesHTML([...f.notes,'这是对文档的解释性重建。虚线步骤按其触发条件插入，图中省略了跳过旁路。写作与原则可贯穿过程，不代表只在图上的一个时间点生效。'])}`;}
else {let list=mode==='interest'?D.interest.map(n=>D.skills[n]):Object.values(D.skills).filter(s=>mode==='principles'?s.kind==='principle':s.kind==='skill');list=list.filter(s=>(s.name+' '+s.role+' '+s.trigger).toLowerCase().includes(query.toLowerCase()));html=`<div class="intro"><h2>${mode==='principles'?'24 个横向原则':mode==='interest'?'你关注的 15 个技能':'34 个工具技能'}</h2><p>${mode==='principles'?'它们按情境约束整个流程，不是另一条 24 步流水线。':mode==='interest'?'左侧选择组合路径；下方卡片查看各技能怎样接入系统。':'包含入口、工作流技能、沟通技能及可单独调用的支线。'}</p></div><div class="catalog">${list.map(s=>`<button class="skillcard ${D.interest.includes(s.name)?'interested':''}" data-skill="${E(s.name)}"><strong>${E(s.name)}</strong><span>${E(s.role)}</span></button>`).join('')||'<div class="empty">没有匹配的技能。</div>'}</div>`;}
$('#content').innerHTML=html;showDetail(selectedSkill);}
document.addEventListener('click',e=>{const b=e.target.closest('[data-mode],[data-flow],[data-extra],[data-skill],#focus');if(!b)return;if(b.id==='focus'){focus=!focus;render();return}if(b.dataset.mode){mode=b.dataset.mode;query='';if(mode==='flows')selectedFlow='feature';if(mode==='interest')selectedFlow='list';render();return}if(b.dataset.flow){mode='flows';selectedFlow=b.dataset.flow;render();return}if(b.dataset.extra){mode='interest';selectedFlow='x:'+b.dataset.extra;render();return}if(b.dataset.skill)showDetail(b.dataset.skill)});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('.node')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}))}});
document.addEventListener('input',e=>{if(e.target.id==='search'){const start=e.target.selectionStart;query=e.target.value;render();const el=$('#search');el.focus();el.setSelectionRange(start,start)}});
$('#mobileMenu').addEventListener('change',e=>{selectedFlow=e.target.value;render()});
window.addEventListener('resize',()=>{const x=$('#mobileMenu');x.style.display=window.innerWidth<=750&&(mode==='flows'||mode==='interest')&&x.options.length?'block':'none'});
window.PSTACK={data:D,render,selectFlow(id){mode='flows';selectedFlow=id;render()},selectMode(m){mode=m;query='';if(m==='interest')selectedFlow='list';render()}};
render();
'''

HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>pstack 技能工作流 · 源码关系图</title><style>__CSS__</style></head><body>
<header><div class="eyebrow">PSTACK / SOURCE-GUIDED WORKFLOW MAP</div><h1>pstack 如何组织一次任务</h1><p>主入口负责路由，playbook 指定步骤，技能完成工作；原则与写作要求贯穿过程。点击节点查看执行逻辑和 GitHub 源文件。</p><div class="meta"><span>34 工具技能</span><span>23 任务流程</span><span>24 原则技能</span><span>main · v0.15.36</span><span>核对于 2026-11-02</span><span>本地离线交互 · 无外部脚本</span></div></header>
<nav aria-label="可视化视图"><button class="active" data-mode="overview">总体路由</button><button data-mode="flows">23 条任务路径</button><button data-mode="interest">你关注的 15 项</button><button data-mode="principles">原则层</button><button data-mode="catalog">全部工具技能</button></nav>
<div class="layout"><aside class="panel sidebar" id="sidebar"></aside><main><select id="mobileMenu" aria-label="选择任务路径"></select><section class="panel content" id="content"></section></main><aside class="panel detail" id="detail" aria-live="polite"></aside></div>
<footer class="foot"><p class="notice">阅读边界：这是一份依据源文件重建的说明图，不会执行技能，也不提供真实任务的验证结论。箭头可表示先后、路由或内部复用，路径中的说明会指出区别。开 PR、检查 PR、合并 PR 是不同阶段。</p><p>Benny 是独立、默认休眠的自动化包，不属于上述 23 条主入口任务路径：setup-benny → 两个自动化（triage-issue-reports → reproduce-and-fix-issues）。它们依赖 Slack / 工单 / 控制适配器，确认复现后只开草稿 PR。</p><div class="footer-links"><a href="https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md" target="_blank" rel="noopener">主路由源码</a><a href="https://github.com/cursor/plugins/tree/main/pstack/skills/poteto-mode/playbooks" target="_blank" rel="noopener">23 个 playbook</a><a href="https://github.com/cursor/plugins/blob/main/pstack/automations/benny/FOR_AGENTS.md" target="_blank" rel="noopener">Benny 自动化包</a></div><p>个人研究产物。main 会继续变化；模型默认值和触发规则以打开的源文件为准。</p></footer>
<script type="application/json" id="data">__DATA__</script><script>__JS__</script></body></html>'''

OUT.mkdir(parents=True, exist_ok=True)
(OUT/'index.html').write_text(HTML.replace('__CSS__',CSS).replace('__DATA__',json.dumps(DATA,ensure_ascii=False).replace('</','<\\/')).replace('__JS__',JS),encoding='utf-8')
(OUT/'workflow-data.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'app-check.js').write_text(JS,encoding='utf-8')
print(f'Built {OUT / "index.html"}: {len(flows)} playbooks, {len(extra)} composition paths, {sum(s["kind"]=="skill" for s in skills.values())} tools, {len(principles)} principles.')
