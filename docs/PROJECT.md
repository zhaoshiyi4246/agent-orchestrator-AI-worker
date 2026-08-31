# v0.2 修正项目基线

- 状态：R1 已完成；当前阶段为 R2，下一步 R2-1
- 权威性：本文件是修正期间的当前架构基线
- 原则：如无必要，勿增实体

## 一、产品定位

本项目是在 Agent Orchestrator（AO）之上构建的闭环多智能体软件开发控制层。

AO 负责 Agent 运行、Session、Chat、worktree、PR/SCM 与可视化；本项目负责 Mission 编排、确定性观察、语义审计、唯一规划裁决、受控 Worker 执行、项目级 Gate、恢复与前端展示。

目标不是替代 AO，也不是构造一个全连接 Agent 网络，而是让以下闭环可追踪、有界、可恢复：

```text
用户目标
  ↓
唯一 Planner
  ↓
按需 Worker
  ↓
Deterministic Observer
  ↓
只读 Auditor
  ↓
唯一 Planner
  ↺

合并候选
  ↓
Integration Gate
  ├─ 通过：结束
  └─ 失败：Auditor / 可选 Verifier → Planner → Worker
```

## 二、当前仓库角色

```text
仓库根目录
├─ README.md
├─ 交付/
│  ├─ closed-loop-v2/               当前 v0.2 主产品候选
│  ├─ clao-src/                     v0.1 历史来源与参考实现
│  ├─ ao-supervision-sidecar/       mission 产品化历史来源与参考实现
│  ├─ closed-loop-demo/             演示目标仓库
│  ├─ closed-loop-demo-origin.git/  演示 bare origin
│  └─ ARCHITECTURE-v0.2.md          与本文件同步的当前架构说明
├─ AGENTS.md
├─ PLANS.md
└─ docs/PROJECT.md
```

R0 已通过入口、import、调用关系和测试复核上述定位。R2 完成具体引用关系证明前，
不删除任何历史来源目录。

## 三、当前实现：R0/R1-4 事实基线

### 1. 当前主入口与控制路径

当前对外主运行入口只有两条，最终复用同一组装路径：

```text
启动面板.bat
  → panel/server.py
  → PanelState.start_mission()
  → run_mission.setup_environment() / load_config() / build_runtime()
  → MissionRuntime
  → MissionController.step()

run_mission.py main()
  → setup_environment() / load_config() / build_runtime()
  → run_loop()
  → MissionController.step()
```

`panel/server.py` 没有第二套 Controller，但它自行实现轮询循环，没有调用
`run_mission.run_loop()`。`loopcore.cli`、`loopcore.closed_loop_cli` 和
`loopcore.mission_cli` 仍可作为旧的监督、单任务和 Mission 兼容入口运行，
但不被面板或 `run_mission.py` 导入。

`MissionRuntime` 直接创建并注入：

- `CodexCliPlannerProvider`、`CodexCliAuditorProvider`、
  `CodexCliVerifierProvider`；
- `ActionExecutor`、`AOAdapter`、`event_observer.Observer`、
  `mission_gate.IntegrationGate`、`StateStore`；
- `MissionController`、`LoopBus`、`StoreBusProjector` 和 `ProjectMemory`。

`MissionController` 再为每个子任务创建 `ClosedLoop`，复用上述 Provider、
AO 边界、Observer、Gate 和 Store，并直接负责恢复、派发、合并、最终 Gate
与最终 Verifier。

### 2. 当前角色的真实运行形态

| 角色 | 物理运行形态 | 默认模型 |
|---|---|---|
| Planner / Auditor / Verifier | headless Codex CLI Provider | `gpt-5.6-sol` |
| Worker | AO Codex Worker（harness=`codex`） | 显式 `--model gpt-5.6-sol` |
| Observer / Integration Gate | 确定性普通程序 | no model |

- Planner、Auditor、Verifier 都不是 AO Session。R1-1/R1-2 已将三个生产
  Provider 分别迁移为 `CodexCliPlannerProvider`、`CodexCliAuditorProvider`
  和 `CodexCliVerifierProvider`；三者复用 `codex_cli.run_codex_json()`，以
  stdin、`--ephemeral`、`--sandbox read-only`、各自现有输出 schema 和
  `--output-last-message` 调用 Codex CLI，默认模型均为可配置的
  `gpt-5.6-sol`。生产主路径不再要求 Claude CLI、`ANTHROPIC_MODEL` 或 GLM
  网关，也不再调用 `llm_env.ensure_llm_env()`。`llm_env.py` 与旧 Provider
  类名仅作为待 R2 调用关系审计的兼容遗留；旧类名是 Codex Provider 的简单别名，
  不保留第二套 Claude 生产实现。
- Worker 由 `ActionExecutor` 调用 `ao.exe spawn --kind worker` 创建，并通过
  `ao send`、`ao session kill` 管理。R1-3 在 AO Desktop `0.12.9` 上验证的真实
  harness 值为 `codex`，Chat 接口使用 `--mode chat`，模型通过
  `--model gpt-5.6-sol` 显式传递。`TaskSpec` 与 `MissionSpec` 缺省均为
  `codex`，生产 `worker.model` 缺省为 `gpt-5.6-sol`；旧 GLM 的
  “先带 model 失败、再去掉 model 重试” fallback 已移除。
- R1-4 修正了 Panel Mission 构造中最后一处显式
  `worker_harness=claude-code` 覆盖。当前 `panel/server.py`、
  `tasks/mission-quick.json`、`MissionSpec`、`TaskSpec` 和 task-spec schema
  均使用 `codex`；Panel 不硬编码 Worker model，`config/default.yaml` 的
  `worker.model=gpt-5.6-sol` 由 `run_mission.py` 注入 `ActionExecutor`。
- `AOAdapter` 通过 AO REST 读取 Project/Session/Conversation/activity，并可
  调用 approval resolve；`ActionExecutor` 承担 AO CLI 写操作。
- `run_mission.py --dry-run` 现已收敛为 Planner 分解预检：解析 Mission 后
  只创建生产 Codex Planner，输出结构化 MissionPlan 并直接退出。该路径不
  创建 `MissionRuntime`、`StateStore`、runtime 目录、AOAdapter、Auditor、
  Verifier、Worker、Gate 或 LoopBus，不连接 AO，也不修改用户项目。它仍会
  发起一次真实模型调用，因此不是离线模式；离线覆盖由 mock 测试提供。

共享 Codex runner 是 Planner/Auditor/Verifier 的统一复用边界。它不持久化
Codex Session、不读取 API Key、不设置 `ANTHROPIC_MODEL`，也不在共享层重试；
角色 Provider 继续负责一次重试和现有本地 validator 的 fail-closed 语义。
PlannerAction 的 transport schema 已显式覆盖 REPLAN 所需的非空
`replacement_task_spec.objective`；共享 runner 不再把未声明 `properties` 的
object schema 静默收窄为空对象，而是在启动 Codex 前 fail closed。

当前 Verifier 仍在每个子任务 Gate 后和 Mission 最终 Gate 后调用；只在终局或
高风险场景按需调用是 R3 目标。当前 Mission 也仍允许多个子任务；默认 1 个
Worker、必要时最多 2 个是 R3 目标，不是 R1 已实现事实。

当前 `ClosedLoop` 还保留一条 deterministic L0 fast path：fresh local error 在
任务仍为 `WORKER_RUNNING`、Worker 不处于进行中的 turn、孵化 grace 已满足且
fingerprint 尚未发送过时，可以直接调用 `ActionExecutor.nudge_worker()`，不经过
Auditor 或 Planner。每个 fingerprint 最多发送一次；重复问题产生 L1 alert 后仍
升级到 Auditor → Planner。该路径属于 MissionController 直接组装的 `ClosedLoop`
控制层，不是第二个控制平面。R3 将决定保留该 fast path，还是统一路由 Planner。

`llm_env.py`、旧 Provider 类名兼容别名、旧审批回归注释，以及
`tasks/mission-quick-002.json` 至 `mission-quick-014.json` 中的旧 harness 字符串
属于兼容或历史运行证据，不进入当前默认生产组装路径。R2 将在引用关系证明后
决定保留、隔离或删除；R1-4 不机械改名或改写历史证据。

### 3. Store、Bus、投影和用户指令

`StateStore` 是当前 Controller 的持久化状态源。它保存 Mission/Task、状态迁移、
预算计数、幂等记录、告警、审计、Planner action、Gate 和 Verifier 结果；
`MissionController._hydrate()` 和 `ClosedLoop` 的恢复路径会读取这些记录，预算
判断和状态迁移也直接读写 Store。AO 的 Session/Conversation/activity 则是
Worker 运行事实来源。

`LoopBus` 当前不改变 Mission/Task 状态，也不向 Agent 投递控制指令。
`StoreBusProjector` 在 Controller 已写入 Store 后追读新行，生成经路由校验的
Envelope，再写入进程内投影列表、`bus_traffic.jsonl` 和 Markdown；未注册的
接收端会被补成 no-op sink。面板状态 API 直接读取 SQLite 和 JSONL，不通过
Bus 恢复或裁决。

用户指令的真实路径是：

```text
panel /api/directive
  → DirectiveChannel
  → MissionController._apply_directives()
  ├─ Planner：追加到 ClosedLoop.instruct
  ├─ Auditor/Verifier：追加到 role_directives
  ├─ Worker：ActionExecutor.nudge_worker() → ao send
  └─ Observer/Gate：仅镜像给 Planner
```

面板另行把指令写入 `bus_traffic.jsonl`；这不等于指令经 `LoopBus` 投递。

### 4. R0 重复实现与入口盘点

| 组 | Panel / `run_mission.py` / Controller 主路径 | 其他实际引用 | R2 候选处置 |
|---|---|---|---|
| `ao_adapter.py` / `ao_client.py` | 使用 `ao_adapter.py`；`ao_client.py` 未进入主路径 | `ao_client.py` 只被旧 `observer.py` 导入 | 保留 Adapter；证明兼容需求后隔离或删除旧 Client/Observer 组合 |
| `event_observer.py` / `observer.py` | 使用 `event_observer.Observer` | `event_observer.py` 也被兼容 CLI 和大量测试使用；`observer.py` 无运行入口引用 | 保留前者；后者与 CL-AO 来源一起审计 |
| `mission_gate.py` / `integration_gate.py` | 使用 `mission_gate.IntegrationGate` | `mission_gate.py` 被兼容 CLI 和测试使用；`integration_gate.py` 无运行入口引用 | 保留前者；后者与 CL-AO 来源一起审计 |
| `mission_contracts.py` / `protocol.py` | 使用 `mission_contracts.py` | contracts 被当前模块和测试广泛使用；`protocol.py` 无运行入口引用 | 保留 contracts；确认无兼容消费者后隔离旧协议 |
| `cli.py` / `closed_loop_cli.py` / `mission_cli.py` / `run_mission.py` | 面板和当前 CLI 只走 `run_mission.py` | `mission_cli.py` 复用另外两个兼容 CLI；`cli.py` 还有一项测试引用 | 保留 `run_mission.py`；R2 逐个证明兼容入口是否保留 |

`closed-loop-v2` 没有从 `clao-src` 或 `ao-supervision-sidecar` 做跨目录 import。
文件哈希表明，v2 的 `observer.py`、`integration_gate.py`、`protocol.py` 与
CL-AO 对应文件相同；v2 的 Mission、Store、Verifier、worktree 和多项 CLI
则由 sidecar 来源继续演化。两套来源目录目前只作为同时交付的历史参考，
R0 不据此删除或移动任何文件。

## 四、后续收敛目标架构

```text
┌─────────────────────────────────────────┐
│ Web Panel / CLI                         │
│ Mission 输入、状态、证据、人工 override │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│ MissionController                       │
│ 唯一控制平面                            │
│                                         │
│ ├─ Planner Provider                     │
│ ├─ Auditor Provider                     │
│ ├─ optional Verifier Provider           │
│ ├─ Deterministic Observer               │
│ ├─ Integration Gate                     │
│ ├─ AOAdapter / ActionExecutor           │
│ └─ Worker / merge orchestration         │
└───────────────┬────────────────┬────────┘
                │                │
      ┌─────────▼────────┐  ┌────▼─────────────┐
      │ StateStore       │  │ AO Desktop       │
      │ 唯一 CL-AO 状态源│  │ Session/worktree │
      └─────────┬────────┘  │ Agent/PR/SCM     │
                │           └──────────────────┘
      ┌─────────▼──────────────────────────────┐
      │ Event Projector / UI Timeline          │
      │ Markdown、JSONL、拓扑图等派生展示      │
      └────────────────────────────────────────┘
```

### 目标 LLM 路径

```text
Planner / Auditor / Verifier
  → 一个共享的 Codex CLI 调用边界
  → codex exec
  → GPT-5.6 Sol

Worker
  → AO Codex Worker
  → GPT-5.6 Sol

Observer / Integration Gate
  → deterministic program
  → no model
```

Planner、Auditor、Verifier 的共享调用边界必须使用 ephemeral、read-only 和
结构化输出；角色 prompt 与任务输入通过 stdin 或等价的安全输入传递。模型输出
仍由现有 schema/validator 在本地严格验证，且不得绕过 `MissionController` 改变
状态或控制 Worker。Verifier 只在终局或高风险场景按需调用，不默认用于每个普通
子任务。默认模型为 `gpt-5.6-sol`，但该值必须可配置，不是永久架构不变量。
默认认证路径复用 Codex CLI / AO Codex 的 ChatGPT 登录额度，不改用 OpenAI API
Key 作为默认接入方式。

## 五、后续目标模块职责

### 1. Web Panel / CLI

负责：

- 接收 Mission、验收条件、约束和项目选择；
- 展示状态、证据、预算、Gate 和最终结果；
- 发起显式人工 override；
- 调用 MissionController 的稳定接口。

不负责：

- 自行裁决；
- 直接修改 StateStore；
- 绕过 Controller 向 Worker 静默注入自动指令。

### 2. MissionController

唯一真实控制平面，负责：

- Mission 状态机；
- 调用 Planner 拆解；
- 决定是否创建第二个 Worker；
- 触发 Observer、Auditor、Gate 和可选 Verifier；
- 预算、超时、恢复、停止和人工兜底；
- 统一写入 StateStore；
- 调用 AOAdapter 执行必要 AO 操作。

不得再创建第二套 Bus 控制平面。

### 3. AOAdapter / ActionExecutor

唯一 AO 接入边界，负责：

- AO 公开 REST/CLI 契约；
- Session 与 activity 读取；
- Worker 创建、消息投递和生命周期操作；
- 必要审批动作；
- 错误标准化与幂等。

不得直接拥有 Mission 级裁决权。

### 4. StateStore

CL-AO 唯一运行状态源，保存：

- Mission、Task、状态迁移；
- Audit、PlannerDecision、VerifierResult、GateRun；
- 预算、恢复索引和幂等记录；
- UI 所需稳定查询数据。

AO Snapshot 仍是 Agent/turn/activity/worktree 的外部事实源。恢复时由 Controller 对二者进行显式校验。

### 5. Event Projector

只从 StateStore/AO 事实生成：

- UI 时间线；
- 事件投影；
- Markdown 摘要；
- JSONL 审计轨迹；
- 拓扑展示。

这些输出不参与运行时恢复、去重、预算或决策。

### 6. Observer

确定性程序，负责：

- MILESTONE；
- REPEATED_FAILURE；
- STALL；
- 越界、预算和风险信号。

只输出 trigger 和 evidence，不输出 PASS/LOCAL_FIX/REPLAN/HUMAN。

### 7. Auditor

只读语义审计者，负责：

- 根据任务目标、验收条件、约束和证据判断问题；
- 向 Planner 提交 AuditReport；
- 请求必要的确定性证据。

不直接向 Worker 下发自动执行指令，不修改代码，不管理 Session。

### 8. Planner

唯一项目级决策者，负责：

- 接收用户高层目标；
- 将任务拆成 1 个或最多 2 个有必要的子任务；
- 根据 Audit、Gate 和 Verifier 证据裁决；
- 向 Worker 下发边界清晰的自动执行指令；
- 统一向用户报告。

默认只使用 1 个 Worker。只有路径独立、依赖清晰且并行收益明确时才启用第 2 个。

### 9. Worker

只执行边界清晰的具体任务，遵守 allowed paths、约束和验收条件，返回真实验证证据。

不承担项目级规划、语义审计或创建其他 Worker。

### 10. Integration Gate

确定性程序，负责：

- 在明确 checkout 上运行显式 argv；
- 检查 exit code、timeout、输出和 Git 不变量；
- 生成稳定证据。

不解释语义，不直接给 Worker 指令。

### 11. Verifier

可选的独立终局/高风险复核：

- 最终合并验收；
- Worker 修改测试；
- Gate 与 Worker 声明矛盾；
- 高风险任务；
- Auditor/Planner 请求独立复核。

只向 Planner 提交证据，不直接控制 Worker。普通子任务不默认调用。

## 六、后续目标控制权与消息方向

以下 Planner-only 自动消息方向是 R3 收敛目标，不是 R1 当前实现事实；当前有界
L0 direct worker nudge 在 R3 作出保留或收敛决定前仍是明确例外。

允许的核心自动路径：

```text
Human → Planner
Planner → Worker
Worker → Controller/Planner（状态与证据）
Observer → Auditor
Auditor → Planner
Gate → Planner 或 Auditor
Verifier → Planner
Planner → Human
```

禁止的自动路径：

```text
Auditor → Worker 执行指令
Verifier → Worker 执行指令
Observer → Worker 执行指令
Bus → 绕过 MissionController 改状态
UI → 绕过 MissionController 改状态
```

用户可显式人工 override 非 Planner 角色，但 Controller 必须记录并暂停或替代冲突的自动 thread。

## 七、后续目标状态与事实源

| 数据 | 权威来源 |
|---|---|
| AO Session、turn、message、activity、workspace | AO 公开快照 |
| Mission、Task、预算、裁决、恢复、UI 状态 | StateStore |
| UI 时间线、Bus 流量、Markdown、JSONL | 派生投影 |
| Git commit、diff、工作区 | Git 与 AO workspace 事实 |

运行时不得从 Markdown、前端缓存或 Bus 内存恢复 Mission。

## 八、R0 已确认的问题与 R1 收敛结果

1. R0 发现旧架构文档把 Planner/Auditor/Verifier 写成 AO Session，并把 Bus
   写成唯一 AO 传输层；R1-4 已将当前文档和前端统一为 headless Provider、
   `MissionController` 控制平面与 Store 后置投影。
2. `closed-loop-v2` 内同时保留两套 AO Client、Observer、Gate、协议和多套
   CLI，其中一套进入主路径，另一套主要是兼容或历史来源。
3. 默认 Mission 的 `max_subtasks=2`，Planner 提示在该值大于 1 时要求拆成
   `2..max_subtasks`，因此当前默认不是单 Worker。
4. Verifier 在每个子任务 Gate 后和 Mission 最终 Gate 后都会调用，不是仅用于
   最终合并或高风险独立复核。
5. `issue_fingerprint()` 把 `source` 写入 key；`LoopBus.resolve_issue()` 只允许
   每个 issue 一次 verdict，没有 revision 语义。
6. Store/AO/投影的代码主从关系已确认；R1-4 已同步 README、交付说明、
   `ARCHITECTURE-v0.2.md` 和前端控制/证据流拓扑。
7. `roles.*.model`、`roles.max_parallel_workers`、`ao.base_url` 等配置没有被
   当前 `run_mission.py` 组装路径完整消费，面板还维护另一组运行时参数。
8. 面板默认且回退到 `closed-loop-demo`，没有从 AO 项目列表选择真实 Project。
9. 自动审批存在；`auto_ff_master` 默认关闭，但面板 API 可开启自动快进和 push，
   两者都需要在 R4 单独审计权限边界。
10. 旧文档曾分别声称 247 或 272 项测试；这些冻结数字已清理。R1-3 的
    `main` 基线为 295 passed，以后以 CI/当前测试输出为准。

## 九、修正阶段

- R0：建立治理文件，确认真实入口、调用关系和测试基线（已完成）；
- R1：Codex Provider、Worker、当前文档和前端拓扑事实统一（已完成）；
- R2：证明并收敛重复模块、旧入口和参考代码；
- R3：收敛 Worker、Verifier、issue/thread 与控制权语义；
- R4：收敛配置、项目选择和高风险功能；
- R5：CI、全新安装、真实 Demo 与干净交付。

## 十、明确非目标

修正期间不以以下内容为目标：

- 增加新 Agent；
- 构造全连接 Agent 网络；
- 新增第二个 Bus、数据库或状态机；
- 默认启动两个以上 Worker；
- 将 Verifier 设为常驻子任务审计者；
- 让 Markdown 成为运行状态源；
- 打包 AO 用户数据或开发机运行状态；
- 自动向用户仓库 push；
- 在未完成架构收敛前继续增加前端功能。
