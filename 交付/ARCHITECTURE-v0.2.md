# v0.2 当前架构说明

> 状态：R1 实现事实基线
>
> 权威架构：与仓库根目录 `docs/PROJECT.md` 保持一致
> 当前主产品候选：`交付/closed-loop-v2/`

本文描述 R1 结束时已经存在的运行路径。逻辑职责关系不等于真实物理消息路径；
R2/R3/R4 的后续目标会明确标注，不提前写成当前能力。

## 一、当前物理控制架构

```text
┌──────────────────────────────────────────┐
│ Web Panel / run_mission                  │
│ Mission 输入、状态查看、人工指令          │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────▼─────────────────────┐
│ MissionController                        │
│ 唯一控制平面                             │
│                                          │
│ ├─ Planner Provider                      │
│ ├─ Auditor Provider                      │
│ ├─ Verifier Provider                     │
│ ├─ Deterministic Observer                │
│ ├─ Integration Gate                      │
│ ├─ AOAdapter / ActionExecutor            │
│ └─ Worker / merge orchestration          │
└───────────────┬─────────────────┬────────┘
                │                 │
      ┌─────────▼─────────┐  ┌────▼──────────────┐
      │ StateStore        │  │ AO Desktop        │
      │ CL-AO 唯一运行    │  │ Session / Agent   │
      │ 状态源            │  │ activity/worktree │
      └─────────┬─────────┘  └───────────────────┘
                │
      ┌─────────▼───────────────────────────────┐
      │ StoreBusProjector / Event Projection    │
      │ JSONL、Markdown、UI Timeline、拓扑展示  │
      └─────────────────────────────────────────┘
```

当前对外入口有两条，并复用同一个 `build_runtime()` 组装路径：

```text
启动面板.bat → panel/server.py → PanelState.start_mission()
  → run_mission.build_runtime() → MissionController.step()

run_mission.py main()
  → build_runtime() → run_loop() → MissionController.step()
```

Panel 自行维护轮询线程，没有调用 `run_loop()`，但没有创建第二套 Controller。

## 二、当前角色与程序

| 角色或程序 | 数量与物理形态 | 默认模型 | 当前职责与控制权 |
|---|---|---|---|
| Planner | 1 个项目级唯一的 headless Codex CLI Provider | `gpt-5.6-sol` | 拆解 Mission、接收 Audit/Gate/Verifier 证据并裁决；不直接编辑代码 |
| Auditor | 1 个只读 headless Codex CLI Provider | `gpt-5.6-sol` | 做语义审计并向 Planner 提交结果；不直接向 Worker 下发自动指令 |
| Verifier | 独立只读 headless Codex CLI Provider | `gpt-5.6-sol` | 当前在子任务 Gate 后和 Mission 终局调用；只输出验证结果，不拥有 Worker 控制权 |
| Worker | AO Chat-mode Codex Worker | `gpt-5.6-sol` | harness=`codex`；在 AO worktree 执行具体编码任务 |
| Observer | 确定性普通程序 | no model | 从 AO 事件产生 trigger 与 evidence，不做语义裁决 |
| Integration Gate | 确定性普通程序 | no model | 运行预配置显式 argv，记录退出码、输出与 Git 证据 |

Planner、Auditor、Verifier 都不是 AO Session。它们通过共享的 Codex CLI
调用边界使用 stdin、`--ephemeral`、`--sandbox read-only`、结构化输出
schema 和本地 validator。默认认证复用 Codex CLI 的 ChatGPT 登录，不以
OpenAI API Key 作为默认接入路径。

Worker 由 `ActionExecutor` 通过 AO CLI 创建和管理：

```text
ao spawn --kind worker --harness codex --mode chat --model gpt-5.6-sol
ao send ...
ao session kill ...
```

Panel Mission payload、`MissionSpec`、`TaskSpec`、当前
`tasks/mission-quick.json` 和 `task-spec.schema.json` 的默认 harness
均为 `codex`；Worker model 由 `config/default.yaml` 的 `worker.model`
进入 `ActionExecutor`，Panel 不另行硬编码 model。

当前系统仍允许 Mission 拆出多个子任务，Panel 默认
`max_subtasks=2`。默认 1 个 Worker、只有任务确实独立时才启用第 2 个，是
R3 目标，不是当前实现不变量。

Verifier 当前仍在每个子任务 Gate 后和 Mission 最终 Gate 后调用。“只在终局
或高风险场景调用”是 R3 目标，不是当前事实。

## 三、控制权与真实消息路径

`MissionController` 是唯一控制平面。Mission/Task 状态迁移、预算、恢复、
Worker 派发、合并、Gate 和 Verifier 调用都由它或其直接组装的
`ClosedLoop` 完成。

核心逻辑职责关系是：

```text
User → MissionController
MissionController → Planner
Planner → ActionExecutor → Worker
Worker → MissionController
Observer → Auditor
Auditor → Planner
Gate → MissionController / Auditor
Verifier → MissionController / Planner
MissionController ↔ StateStore
MissionController ↔ AO
```

其中主语义闭环是：

```text
Observer → Auditor → Planner → ActionExecutor → Worker
Gate / Verifier evidence → Planner → ActionExecutor → Worker
```

这张逻辑关系图不表示存在对应的点对点物理 Agent 通道。特别是：

- Auditor 不直接向 Worker 自动投递 `LOCAL_FIX`；
- Verifier 不直接向 Worker 投递 `FIX_REQUEST`；
- Observer 不直接控制 Worker；
- 项目级语义裁决权属于唯一 Planner；
- Gate 和 Verifier 结果先进入 Controller/Store，再成为 Planner 可用证据。

### 当前有界 L0 例外

当前 `ClosedLoop._maybe_l0_nudge()` 对 fresh local error 保留一条
deterministic fast path：在任务仍为 `WORKER_RUNNING`、Worker 不处于进行中的
turn、孵化 grace 已满足且该 fingerprint 尚未发送过时，它可以直接调用
`ActionExecutor.nudge_worker()`。该路径不调用 Auditor 或 Planner，每个 fingerprint
最多一次；重复问题产生 L1 alert 后仍升级到 Auditor → Planner。

这条路径位于 MissionController 直接组装的 `ClosedLoop` 控制层内，AO 写操作仍经
`ActionExecutor`，不是第二个控制平面。它是当前实现事实，不是目标不变量；R3
将决定保留该 fast path，还是把它统一收敛到 Planner 控制。

用户指令的真实路径是：

```text
Panel /api/directive
  → DirectiveChannel
  → MissionController._apply_directives()
     ├─ Planner：写入 ClosedLoop.instruct
     ├─ Auditor/Verifier：写入对应 role_directives
     ├─ Worker：ActionExecutor.nudge_worker() → ao send
     └─ Observer/Gate：只镜像给 Planner
```

面板另外把用户指令写入 `bus_traffic.jsonl` 用于展示；这不是指令经
`LoopBus` 投递。

## 四、状态源与恢复

| 数据 | 当前权威来源 |
|---|---|
| Mission、Task、状态迁移、预算、审计、Planner action、Gate、Verifier、恢复索引 | `StateStore` |
| Worker Session、Conversation、turn、activity、workspace/worktree | AO 公开快照 |
| Git commit、diff、工作区 | Git 与 AO workspace 事实 |
| UI 时间线、Bus traffic、Markdown、JSONL、拓扑 | 派生投影 |

`StateStore` 不是辅助索引，而是 CL-AO Mission/Task/预算/裁决/恢复的唯一
运行状态源。AO Snapshot 则是 Worker 运行状态的外部事实源。Controller 恢复
时读取 Store，并按需与 AO 事实核对。

`memory.md`、`project.md` 和 `bus_traffic.jsonl` 位于
`closed-loop-v2/runtime/<mission_id>/`，不写入目标项目根目录，也不参与
恢复或裁决。

## 五、LoopBus 的当前定位

`LoopBus` 当前不是控制总线，也不是唯一 AO 传输层。
`StoreBusProjector` 在 Controller 已写入 StateStore 后追读新行，将其转换为
经过路由和预算校验的 Envelope，再写入：

- 进程内投影列表；
- `bus_traffic.jsonl`；
- `memory.md` / `project.md`；
- Panel 的事件时间线。

投影接收端当前是 no-op sink；投影失败记录在 `StoreBusProjector.errors`，
不会回写控制状态。真实 AO 读取由 `AOAdapter` 完成，真实 Worker 写操作由
`ActionExecutor` 完成。

因此：

```text
StateStore / AO facts
        ↓
StoreBusProjector
        ↓
Event Projection / Audit Timeline / UI
```

Bus traffic、Markdown、JSONL、拓扑和前端缓存均为派生视图，不用于运行时
恢复、去重、预算判断或裁决。

## 六、当前已实现

- Panel 发起 Mission，CLI/Panel 复用运行时组装；
- Planner 自动分解；
- AO Codex Worker 执行；
- Observer 确定性观察；
- Auditor → Planner 闭环；
- Integration Gate；
- 当前子任务级与 Mission 终局 Verifier；
- StateStore 持久化和恢复；
- stop/resume；
- Store 后置投影与 UI 时间线。

当前 `main` 基线在 R1-3 验证时为 **295 passed**；以后以 CI/当前测试输出为准。

## 七、后续边界

- R2：生成主路径引用图，逐组证明并收敛重复 AO Client、Observer、Gate、
  协议和旧 CLI；在此之前不删除参考目录或兼容模块。
- R3：默认 1 个 Worker、必要时最多 2 个；收敛 Verifier 调用策略、
  issue fingerprint 和 thread revision；决定保留当前有界 L0 fast path，还是将
  自动 Worker 指令统一由 Planner 发出。
- R4：通用 AO Project 选择、配置真实消费、人工 override、审批白名单，
  保持自动 push/merge 默认关闭。
- R5：CI、全新 clone 安装、AO 官方依赖说明、路径可移植性、真实 Demo 和
  干净交付。

当前生产主路径不使用 `llm_env.py`。该文件、旧 Provider 类名兼容别名，
以及 `tasks/mission-quick-002.json` 至 `mission-quick-014.json` 中保留的
旧 harness 值属于兼容或历史运行证据，不是当前默认入口；R2 在调用关系证明后
再决定保留、隔离或删除。

## 八、当前不变量

1. `MissionController` 是唯一控制平面；
2. `StateStore` 是唯一 CL-AO 运行状态源；
3. AO Snapshot 是 Worker 运行事实源；
4. Observer 和 Integration Gate 是确定性程序，不使用模型；
5. Auditor 只读并只向 Planner 提交审计结果；
6. Verifier 只输出证据，不直接控制 Worker；
7. Planner 项目级唯一并拥有项目级语义裁决权；Auditor、Verifier、Observer
   不直接向 Worker 下发语义修复指令；当前 `ClosedLoop` 仍保留一个有界的
   deterministic L0 local-error nudge；
8. Bus 和所有展示产物都是派生投影，不参与恢复或裁决；
9. 模型与 harness 可配置，当前默认契约为 Codex / `gpt-5.6-sol`；
10. 自动 push、自动合并和破坏性审批保持默认关闭。

“所有自动 Worker 指令统一由 Planner 发出”是 R3 收敛目标，不是 R1 当前实现
不变量。
