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

## AO 运行时与首次安装边界

R2-0 已移除当前生产主路径中的开发者绝对 AO 路径。AO Desktop 是外部依赖，
不随本仓库源码打包、安装或自动启动：

- AO executable：先读取 `CLAO_AO_BIN`，未设置时从 PATH 查找 `ao`；
- daemon runfile：先读取 `CLAO_AO_RUN_FILE`，未设置时使用
  `~/.ao/running.json`；
- 正常 Mission 启动和恢复找不到 AO executable 时会立即报错；只读查看已有
  Mission 存档不要求 AO executable，也不会连接 AO、调用 Codex 或创建 Worker。

这解决的是“运行时路径可移植性”，不是“任意用户零配置安装”。clean clone 的
首次 bootstrap/安装脚本、AO 首次配置体验以及 Project 注册/选择尚未完成；当前
仓库不能宣称为通用安装包或“解压即用”产品。

## 后续顺序

1. 合并 PR #6 的 AO 运行时可移植性修复；
2. 运行一次完整真实 E2E Mission；
3. Competition behavior convergence：默认 1 个 Worker、确有必要时最多 2 个，
   Verifier 默认只在 final/终局调用，并把 `auto_ff_master` 隐藏或明确标记为
   实验性高风险功能；
4. 再生成主路径引用图并清理重复模块和旧入口；
5. 最后完成 clean delivery、installer/bootstrap 与 first-run 收尾。

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
仅当 AO 使用非标准 runfile 时才需要设置 `CLAO_AO_RUN_FILE`。

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

测试数量以 CI 或当前真实命令输出为准，不在用户文档中冻结。

## 安全边界

- 自动 push、自动合并和破坏性审批默认关闭；
- Planner/Auditor/Verifier 使用只读、ephemeral、结构化输出的 Codex CLI 调用；
- Observer 和 Gate 不使用模型；
- Markdown、JSONL、前端缓存和拓扑图不作为运行状态源；
- 不把 AO 用户数据、会话、凭据、Cookie、运行数据库或本机缓存作为交付内容。
