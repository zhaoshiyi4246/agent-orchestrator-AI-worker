# closed-loop-v2

当前 v0.2 主产品候选。权威架构见仓库根目录
[`docs/PROJECT.md`](../../docs/PROJECT.md)，交付侧说明见
[`../ARCHITECTURE-v0.2.md`](../ARCHITECTURE-v0.2.md)。

## 首次安装

Prerequisites：

- Windows；
- CPython 3.12.x；
- Git（运行 Mission 时需要）；
- AO Desktop/CLI（运行 Mission 时需要）；
- Codex CLI，并已使用 ChatGPT 登录（运行 Mission 时需要）。

方式 A：双击 `启动面板.bat`。缺少 `.venv` 或必要 Python package 时，启动器会
自动运行 `bootstrap.ps1`，然后启动 Panel。

方式 B：在本目录手动运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1
```

bootstrap 只创建本目录的 `.venv` 并安装 `requirements.txt` 中的 Python package；
它不会安装 Python、Git、AO 或 Codex，也不会连接 AO 或调用模型。

真实 Mission 启动前，Panel 与 CLI 复用同一 preflight：检查当前进程为 CPython
3.12、选中 AO Project 是具有有效 Git identity 的 Git worktree、AO daemon/API
可读取该 Project、Codex CLI 已通过 ChatGPT 登录，以及四个生产模型配置非空。
preflight 不安装外部工具、不调用模型，也不检查目标项目自己的 Gate dependencies。

安装后可执行自验证：

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests -q
```

## 运行路径

```text
panel/server.py 或 run_mission.py
  → 共用 build_runtime()
  → MissionController（唯一控制平面）
  ├─ CodexCliPlannerProvider
  ├─ CodexCliAuditorProvider
  ├─ CodexCliVerifierProvider
  ├─ event_observer.Observer（无模型）
  ├─ mission_gate.IntegrationGate（无模型）
  ├─ ActionExecutor / AOAdapter → AO Codex Worker
  └─ StateStore（唯一 CL-AO 运行状态源）
       → StoreBusProjector → JSONL / Markdown / UI Timeline
```

Planner、Auditor、Verifier 使用 headless Codex CLI，默认模型均为
`gpt-5.6-sol`。Worker 使用 AO Chat-mode `codex` harness，默认模型由
`config/default.yaml` 的 `worker.model` 提供，同样为 `gpt-5.6-sol`。
VerifierProvider 仍是正式角色：新 Mission 正常路径只在 Mission 终局调用
Verifier；历史 `VERIFIER_PENDING` Task 恢复仍可调用 task verifier。高风险
子任务的显式按需策略尚未实现。

`LoopBus` 当前只承载 Store 后置事件投影、路由校验、审计时间线和 UI 展示；
它不改变 Mission/Task 状态，也不负责真实 Agent 指令投递。Markdown、JSONL
和前端缓存都是派生视图。

## 主要目录

```text
run_mission.py             CLI 与统一运行时组装
panel/server.py            Panel 后端，复用 build_runtime()
panel/index.html           单页展示与真实控制/证据流拓扑
src/loopcore/mission.py    MissionController
src/loopcore/state_store.py
src/loopcore/action_executor.py
src/loopcore/bus_projector.py
config/default.yaml
schemas/
prompts/
tasks/mission-quick.json
tasks/e2e-smoke.json       固定标准 E2E 输入（不自动执行）
tests/
```

`tasks/e2e-smoke.json` 是标准 smoke template，`tasks/mission-quick.json` 是 operator
template。两者的 `project_id` 均为 `REPLACE_WITH_AO_PROJECT_ID`；CLI 运行前必须复制
或修改为 AO 中已注册 Project 的真实 ID，并在重复执行时换成唯一 `mission_id`。
placeholder 会在创建 runtime 前得到明确错误。正常使用 Panel 时，通过 Project
selector 选择真实 AO Project，无需编辑 template。不得删除旧 `runtime` 来伪装成
新 Mission。

## 当前边界

- Panel `GET /api/projects` 通过现有 `AOAdapter.get_projects()` 读取 AO 官方
  Project registry，只返回 `id/name/path/kind`。新建 Mission 时用户选择一个已注册
  Project，浏览器只提交 `project_id`；后端启动前重新查询 AO 并要求对应 path 为
  现存目录。缺失/未知 ID、无效 path 或 AO 不可用都会明确失败，不启动
  runtime/Worker，也不伪造 demo Project。
- 新 Mission 默认 `max_subtasks=1`：Controller 确定性生成唯一 S1，不调用
  decomposition Planner。Panel 只接受 1 或 2；显式选择 2 时 Planner 可返回
  1 或 2，默认优先 1，仅在有真实独立并行收益时使用第二 Worker。越界的新 Mission
  明确拒绝；历史已持久化的 2-task 或更多 task 计划仍可恢复。
- 证据充分的首次普通 Task completion：`Worker idle → deterministic Task Gate →
  DONE`。资格要求为 `WORKER_RUNNING`、明确
  idle/waiting_input/needs_input/exited/terminated、无 pending
  approval、无本 tick actionable alert 或待处理 L0 fresh error、至少一个非空
  Gate 命令、AO workspace 可解析，且 Git `changed_paths` 可审计并至少有一个
  non-artifact change。新 Task Gate PASS 不调用 Completion Auditor、completion
  Planner 或 Task Verifier，也不写 task-level verification row。
- 空 Gate、无变更、Git change set 未知、workspace 不可解析等证据不足情况继续走
  Completion Auditor → Planner；Gate FAIL 继续走 `GATE_PENDING → AUDIT_PENDING
  → Auditor → Planner`。不是所有 Task 都绕过 Completion Auditor。
- 历史 runtime 若已处于 `VERIFIER_PENDING`，仍按旧 task verifier 路径恢复。
- 当前 Mission final path：`materialization → integration → Final Gate → Mission
  Verifier → MISSION_DONE / HUMAN`。Mission Verifier 是新 Mission 默认唯一的
  正常路径 Verifier 调用。`MISSION_DONE` 只表示 verified integration 已通过 Final
  Gate 与 Mission Verifier，结果保留在 `runtime/<mission-id>/integration`；不会
  自动修改用户 `master`/`main`，也不会 push `origin`。未来主分支交付应是用户
  显式 SCM 操作，不是 Mission DONE 隐式副作用。
- Panel 已删除 `closed-loop-demo` 隐式 fallback。Project 注册、修改仍由 AO 负责；
  CL-AO 只读发现并选择已注册项目。历史 Mission 查看/resume 保留其持久化的
  `project_id`，不受当前 selector 值影响；`run_mission.py` CLI 仍通过 Mission JSON
  显式提供 `project_id`，不增加 selector 语义。
- AO runtime discovery/path contract 已完成可移植化，legacy `AO_DATA_DIR` parallel
  runtime 已在 R2 收敛。R5-2 已提供 clean-machine Python bootstrap；R5-3 增加了
  shared Mission preflight，并以 `交付/release-manifest.txt` 为唯一 allowlist authority，
  由 `交付/build-release.ps1` 从 clean HEAD 构建 repo 外 artifact。clean-release
  rehearsal 与真实 AO/Codex 彩排仍待 R5-4/R5-5。
- Competition runtime 不提供自动 push。

## 验证

```powershell
$venvScripts = (Resolve-Path ".\.venv\Scripts").Path
$env:PATH = "$venvScripts;$env:PATH"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

.\.venv\Scripts\python.exe -m pytest .\tests -q
.\.venv\Scripts\python.exe -m compileall -q .\src .\panel .\run_mission.py
.\.venv\Scripts\python.exe .\run_mission.py .\tasks\mission-quick.json --dry-run
```

`--dry-run` 在 `max_subtasks=1` 时输出确定性计划且不调用模型；值为 2 时才调用
只读、ephemeral 的 Codex Planner。测试数量以 CI 或当前真实命令输出为准。
