# 闭环多智能体系统 v0.2

本项目是在 Agent Orchestrator（AO）之上运行的闭环软件开发控制层。AO 提供
Project、Session、Conversation、Agent Runtime、worktree 和 PR/SCM 能力；
本项目负责 Mission 编排、确定性观察、语义审计、受控 Worker 执行、集成门禁、
恢复和 UI 展示。

当前权威架构见 [`docs/PROJECT.md`](docs/PROJECT.md)。`交付/closed-loop-v2/`
是当前 v0.2 主产品候选路径。

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
| Planner | 1 个项目级唯一的 headless Codex CLI Provider | `gpt-5.6-sol` | 自动拆解、接收证据并裁决；不直接编辑代码 |
| Auditor | 1 个只读 headless Codex CLI Provider | `gpt-5.6-sol` | 语义审计，只向 Planner 提交结果，不直接控制 Worker |
| Verifier | 独立只读 headless Codex CLI Provider | `gpt-5.6-sol` | 当前在子任务 Gate 后和 Mission 终局复核，只输出验证结果 |
| Worker | AO Chat-mode Codex Worker，harness=`codex` | `gpt-5.6-sol` | 在 AO worktree 中执行边界明确的编码任务 |
| Observer | 确定性程序 | no model | 从 AO 事实产生触发和证据 |
| Integration Gate | 确定性程序 | no model | 运行显式 argv 门禁并记录稳定证据 |

当前系统允许一个 Mission 拆出多个子任务；“默认 1 个 Worker、确有独立并行收益
时最多 2 个”是 R3 的收敛目标，不是当前实现不变量。Verifier 当前仍用于每个
子任务 Gate 后和 Mission 终局；“只在终局/高风险调用”同样是 R3 目标。

## 当前已经实现

- Panel 发起 Mission，CLI 与 Panel 复用同一运行时组装路径；
- Planner 自动分解；
- AO Codex Worker 执行，Panel 与 CLI 均使用 `codex` harness；
- Observer 确定性观察；
- Auditor 向 Planner 提交审计结果并形成闭环；
- Integration Gate 和当前 Verifier；
- StateStore 持久化及恢复；
- stop/resume；
- Store 后置事件投影和 UI 时间线。

## 后续阶段

- R2：生成主路径引用图，逐组证明并收敛重复模块和旧入口；
- R3：默认单 Worker、按需第二 Worker，收敛 Verifier、issue/thread 与控制权语义；
- R4：通用 AO Project 选择、生效配置、人工 override 和自动审批权限；
- R5：AO 路径与安装可移植性、CI、全新安装验证和干净交付。

当前没有承诺“任意电脑解压即可运行”。AO Desktop 需要单独安装和配置，
`run_mission.py` 中仍存在待 R4/R5 收敛的本机 AO 路径。

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

```powershell
cd 交付/closed-loop-v2
$venvScripts = (Resolve-Path ".\.venv\Scripts").Path
$env:PATH = "$venvScripts;$env:PATH"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

.\.venv\Scripts\python.exe -m pytest .\tests -q
.\.venv\Scripts\python.exe run_mission.py .\tasks\mission-quick.json --dry-run
.\.venv\Scripts\python.exe .\panel\server.py
```

`--dry-run` 会真实调用一次只读、ephemeral 的 Codex Planner，但不会连接 AO、
创建 Worker、StateStore 或 runtime 目录。真实 Mission 运行需要 AO daemon 和
已注册 Project。

当前 `main` 基线在 R1-3 验证时为 **295 passed**；以后以 CI/当前测试输出为准。

## 安全边界

- 自动 push、自动合并和破坏性审批默认关闭；
- Planner/Auditor/Verifier 使用只读、ephemeral、结构化输出的 Codex CLI 调用；
- Observer 和 Gate 不使用模型；
- Markdown、JSONL、前端缓存和拓扑图不作为运行状态源；
- 不把 AO 用户数据、会话、凭据、Cookie、运行数据库或本机缓存作为交付内容。
