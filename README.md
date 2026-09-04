# 闭环多智能体系统 v0.2

本项目是在 Agent Orchestrator（AO）之上运行的闭环软件开发控制层。AO 提供
Project、Session、Conversation、Agent Runtime、worktree 和 PR/SCM 能力；
本项目负责 Mission 编排、确定性观察、语义审计、受控 Worker 执行、集成门禁、
恢复和 UI 展示。

当前权威架构见 [`docs/PROJECT.md`](docs/PROJECT.md)。`交付/closed-loop-v2/`
是当前 v0.2 主产品候选路径。

## 首次安装

Windows 用户需预先安装 CPython 3.12.x。进入 `交付/closed-loop-v2/` 后可直接
双击 `启动面板.bat`；启动器会在需要时运行 `bootstrap.ps1`，创建本地 `.venv`
并安装精确固定的 Python 依赖。也可以手动执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1
```

bootstrap 不安装 Python、Git、AO Desktop/CLI 或 Codex CLI。Git、AO，以及已通过
ChatGPT 登录的 Codex CLI 在实际运行 Mission 时仍是外部 prerequisite。

## 当前真实架构

```text
Web Panel / run_mission
        ↓
MissionController（唯一控制平面）
        ├─ Planner Provider
        ├─ Auditor Provider
        ├─ Verifier Provider
        ├─ Deterministic Observer
        ├─ Integration Gate
        ├─ AOAdapter / ActionExecutor
        └─ Worker / merge orchestration
        ├─↔ StateStore
        └─↔ AO

StateStore
        ↓
StoreBusProjector / JSONL / Markdown / UI Timeline
```

- `MissionController` 是唯一控制平面。
- `StateStore` 是 CL-AO Mission、Task、预算、裁决和恢复的唯一运行状态源。
- AO 的公开 Session、Conversation、activity 和 workspace 快照是 Worker
  运行事实源。
- `LoopBus` 当前用于事件 Envelope 投影、审计轨迹和 UI 时间线，不改变
  Mission/Task 状态，也不承担 Agent 指令的真实投递。
- Markdown、JSONL、Bus traffic 和前端拓扑都是派生视图，不参与恢复或裁决。

用户指令的真实路径是：

```text
Panel → DirectiveChannel → MissionController
Worker 指令：MissionController → ActionExecutor → AO
```

## 当前角色与运行形态

| 角色或程序 | 当前运行形态 | 默认模型 | 当前职责 |
|---|---|---|---|
| Planner | 1 个项目级唯一的 headless Codex CLI Provider | `gpt-5.6-sol` | 仅在允许第二 Worker 时按需拆解，并接收证据裁决；不直接编辑代码 |
| Auditor | 1 个只读 headless Codex CLI Provider | `gpt-5.6-sol` | 语义审计，只向 Planner 提交结果，不直接控制 Worker |
| Verifier | 独立只读 headless Codex CLI Provider | `gpt-5.6-sol` | 新 Mission 正常路径只在 Mission 终局调用；历史 `VERIFIER_PENDING` Task 恢复仍可调用 |
| Worker | AO Chat-mode Codex Worker，harness=`codex` | `gpt-5.6-sol` | 在 AO worktree 中执行边界明确的编码任务 |
| Observer | 确定性程序 | no model | 从 AO 事实产生触发和证据 |
| Integration Gate | 确定性程序 | no model | 运行显式 argv 门禁并记录稳定证据 |

新 Mission 默认 `max_subtasks=1`。该值为 1 时，`MissionController` 确定性生成
唯一 `<mission-id>-S1` 标准计划，不调用 decomposition Planner；用户显式选择 2
时，Planner 可以返回 1 或 2 个子任务，并应优先单任务，只有存在真实独立并行
收益才启用第二 Worker。Panel 只接受 1 或 2，不会把越界值静默 clamp。历史已
持久化计划（包括多于 2 个 task）仍按原计划 hydrate，不重新分解。

证据充分的首次普通 Task completion 采用 deterministic gate-first：Worker 必须
明确 idle/waiting_input/needs_input/exited/terminated、无 pending approval、无本
tick actionable alert 或待处理 L0 fresh error，并且至少有一个非空 Gate 命令、
AO workspace 可解析、Git `changed_paths` 可审计且至少包含一个 non-artifact
change。

```text
Worker
→ deterministic Task Gate
→ DONE
```

任一条件不足（包括空 Gate、`changed_paths == []` 或 `None`）仍走 Completion
Auditor → Planner。Gate FAIL 也仍从 `GATE_PENDING` 进入 `AUDIT_PENDING`，再由
Auditor → Planner 裁决；不是所有 Task 都绕过 Completion Auditor。新 Task 的
Gate PASS 不调用 Task Verifier，也不写 task-level verification row。历史 runtime
若已经处于 `VERIFIER_PENDING`，仍按旧 task verifier 路径恢复。

当前 Mission final path 是：

```text
materialization
→ integration
→ Final Gate
→ Mission Verifier
→ MISSION_DONE / HUMAN
```

Mission Verifier 是新 Mission 默认唯一的正常路径 Verifier 调用。VerifierProvider
仍是正式角色；高风险子任务的显式按需策略尚未实现。`MISSION_DONE` 表示
verified integration 已通过 Final Gate 与 Mission Verifier；结果保留在
`runtime/<mission-id>/integration`。Competition runtime 不会因此修改用户仓库的
`master`/`main`，也不会 push `origin`。若未来需要把结果交付到主分支，应设计为
用户显式发起的 SCM 操作，不是 Mission 完成的隐式副作用。

## 当前已经实现

- Panel 发起 Mission，CLI 与 Panel 复用同一运行时组装路径；
- Panel 通过现有 `AOAdapter.get_projects()` 读取 AO 官方 Project registry；用户
  新建 Mission 时从已注册 Project 中选择，浏览器只提交 `project_id`，后端在启动
  runtime/Worker 前重新查询 AO 并确认对应 `path` 是现存目录；
- 单 Worker Mission 确定性规划；仅双 Worker 候选调用 Planner 分解；
- AO Codex Worker 执行，Panel 与 CLI 均使用 `codex` harness；
- Observer 确定性观察；
- 证据不足或异常时由 Auditor 向 Planner 提交审计结果并形成闭环；
- deterministic Task Gate、Mission Final Gate 和 Mission Verifier；
- StateStore 持久化及恢复；
- stop/resume；
- Store 后置事件投影和 UI 时间线。

## AO 运行时与首次安装边界

R2-0 已移除当前生产主路径中的开发者绝对 AO 路径。AO Desktop 是外部依赖，
不随本仓库源码打包、安装或自动启动：

- AO executable：先读取 `CLAO_AO_BIN`，未设置时从 PATH 查找 `ao`；
- daemon runfile：先读取 `CLAO_AO_RUN_FILE`，未设置时使用
  `~/.ao/running.json`；
- 正常 Mission 启动和恢复找不到 AO executable 时会立即报错；只读查看已有
  Mission 存档不要求 AO executable，也不会连接 AO、调用 Codex 或创建 Worker。
- `CLAO_AO_DATA_DIR` 已无当前 v0.2 正常生产消费者；旧自动 master 写回 helper
  已删除，不会迁移到当前 integration 路径。legacy `AO_DATA_DIR` parallel runtime
  已在 R2 收敛，当前 runtime 只使用正式 portable AO boundary。

这解决的是“运行时路径可移植性”，不是“任意用户零配置安装”。Panel 已能选择
AO 中的已注册 Project，但不会创建、注册或修改 Project；Project 注册仍由 AO
负责。clean-machine Python bootstrap 已提供；AO/Codex/Git Mission preflight、
AO 首次配置体验与最终 release builder 仍未完成，因此当前仓库仍不能宣称为通用
安装包或“解压即用”产品。

## 后续顺序

1. Verifier final-only 已完成，PR #11 后同题 E2E 为 `646.116s`；
2. gate-first happy path 与 event-freshness 修复已完成；
3. 新 Mission 默认 1 个 Worker、按需最多 2 个已完成；标准 smoke
   `MISSION-E2E-SMOKE-20260902-204459` 已到达 `MISSION_DONE`；
4. Competition runtime 的自动 master/main merge 与 origin push 已移除；
5. R4 Project selector 已接入 AO 官方 registry，并移除 Panel 的
   `closed-loop-demo` 隐式 fallback；
6. R2 duplicate / legacy convergence 已关闭，当前 v2 production authority 单一；
7. R5 从 Clean Release Boundary Audit 开始，再处理 clean delivery、
   installer/bootstrap 与 first-run。

fingerprint 去 source 和 thread revision 继续作为低优先级治理项，不阻塞比赛
行为收敛。

## 仓库结构

```text
仓库根目录
├─ docs/PROJECT.md                  当前权威架构
├─ PLANS.md                         阶段、任务与验证证据
└─ 交付/
   ├─ closed-loop-v2/               当前 v0.2 主产品候选
   ├─ clao-src/                     历史来源与参考实现
   ├─ ao-supervision-sidecar/       历史来源与参考实现
   ├─ closed-loop-demo/             演示目标仓库
   ├─ closed-loop-demo-origin.git/  演示 bare origin
   └─ ARCHITECTURE-v0.2.md          与权威架构同步的当前说明
```

历史来源目录在 R2 完成引用关系证明前不会删除，也不是第二套正式产品入口。

## 开发环境运行

已验证环境使用 Windows、Python 3.12、本地
`交付/closed-loop-v2/.venv`、单独运行的 AO Desktop，以及已通过 ChatGPT
登录的 Codex CLI。

启动真实 Mission 前，需要先安装并运行 AO Desktop。若 `ao` 已在 PATH 中，无需
额外设置 executable；否则在当前进程中将 `CLAO_AO_BIN` 指向已安装 AO CLI。
仅当 AO 使用非标准 runfile 时才需要设置 `CLAO_AO_RUN_FILE`。Project 注册由 AO
完成；Panel 的 `GET /api/projects` 只读展示 AO 已注册项目，新建 Mission 时必须
显式选择一个。AO 不可用、ID 未知或对应路径不是现存目录时，Panel 不会启动
runtime/Worker，也不会伪造 demo Project。

```powershell
cd 交付/closed-loop-v2
$venvScripts = (Resolve-Path ".\.venv\Scripts").Path
$env:PATH = "$venvScripts;$env:PATH"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

.\.venv\Scripts\python.exe -m pytest .\tests -q
.\.venv\Scripts\python.exe run_mission.py .\tasks\mission-quick.json --dry-run
.\.venv\Scripts\python.exe .\panel\server.py
```

`run_mission.py` CLI 仍通过 Mission JSON 显式读取 `project_id`，不使用 Panel
selector。`--dry-run` 不会连接 AO、创建 Worker、StateStore 或 runtime 目录；
`max_subtasks=1` 时直接输出确定性单任务计划且不调用模型，值为 2 时才调用一次
只读、ephemeral 的 Codex Planner。真实 Mission 运行需要 AO daemon 和已注册
Project。`tasks/e2e-smoke.json` 是固定回归输入，不会被自动执行。
它当前仅是标准 smoke fixture/template；直接通过 CLI 重复执行前必须使用新的唯一
`mission_id`，Panel 后续若增加“标准 Smoke”入口，应自动生成唯一 Mission ID，
不得删除旧 `runtime` 来伪装成新 Mission。

测试数量以 CI 或当前真实命令输出为准，不在用户文档中冻结。

## 安全边界

- Mission 完成不会自动 merge/push 或修改用户 `master`/`main`；自动 push 不属于
  competition runtime；
- Planner/Auditor/Verifier 使用只读、ephemeral、结构化输出的 Codex CLI 调用；
- Observer 和 Gate 不使用模型；
- Markdown、JSONL、前端缓存和拓扑图不作为运行状态源；
- 不把 AO 用户数据、会话、凭据、Cookie、运行数据库或本机缓存作为交付内容。
