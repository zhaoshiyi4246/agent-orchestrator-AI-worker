# closed-loop-v2

当前 v0.2 主产品候选。权威架构见仓库根目录
[`docs/PROJECT.md`](../../docs/PROJECT.md)，交付侧说明见
[`../ARCHITECTURE-v0.2.md`](../ARCHITECTURE-v0.2.md)。

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
tests/
```

## 当前边界

- 当前系统允许一个 Mission 拆分为多个子任务；默认单 Worker、按需第二 Worker
  是 R3 目标。
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
  正常路径 Verifier 调用。
- 面板目前默认使用演示 Project；通用 AO Project 选择属于 R4。
- AO 路径和安装尚未完全可移植，不能视为解压即用产品。

## 验证

```powershell
$venvScripts = (Resolve-Path ".\.venv\Scripts").Path
$env:PATH = "$venvScripts;$env:PATH"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

.\.venv\Scripts\python.exe -m pytest .\tests -q
.\.venv\Scripts\python.exe -m compileall -q .\src .\panel .\run_mission.py
.\.venv\Scripts\python.exe .\run_mission.py .\tasks\mission-quick.json --dry-run
```

当前 `main` 基线在 R1-3 验证时为 **295 passed**；以后以 CI/当前测试输出为准。
