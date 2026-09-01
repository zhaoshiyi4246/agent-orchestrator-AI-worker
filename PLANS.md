# v0.2 修正计划

- 当前阶段：第一次真实 GUI E2E blocker 修复
- 当前任务：修复 active Worker 的语义审计时序，以及 Auditor/Verifier provider failure 与业务 verdict 的边界
- 当前状态：GUI E2E 已验证 Panel → Planner → AO Codex Worker → official Session workspace API → Observer；Worker 实现正确，失败来自过早 audit 与 transport timeout 被伪装成 semantic HUMAN
- 下一步：本 PR 审计合并后重跑同一 GUI smoke；通过后进入 Competition behavior convergence，不直接进入 R2-1

## 一、更新规则

本文件需要动态维护，但只在以下情况更新：

- 阶段或任务状态改变；
- 真实测试、dry-run 或 live 证据改变；
- 已知问题被证实、否定或关闭；
- 下一步发生变化。

不得写入：

- 单次提示词全文；
- 对话记录；
- 私人路径、凭据、会话内容；
- 未经运行验证的“已完成”结论；
- 大段终端日志。

每个 PR 只更新与本任务直接相关的条目。

## 二、阶段总览

| 阶段 | 目标 | 状态 |
|---|---|---|
| R0 | 修正基线、治理文件、真实入口与测试基线 | 已完成 |
| R1 | Codex Provider 迁移、架构事实、文档、代码注释与前端拓扑统一 | 已完成 |
| R2 | AO 主路径可移植性；重复模块、旧入口和参考代码收敛 | 进行中（R2-0 workspace API；重复清理延后） |
| R3 | Competition behavior convergence：Worker、Verifier、auto_ff；issue/thread 低优先级 | 未开始（完整 E2E 后优先） |
| R4 | 配置有效性、项目选择和高风险功能收敛 | 未开始 |
| R5 | CI、全新安装、真实 Demo 与干净交付 | 未开始 |

## 三、R0 验收条件

R0 只做基线，不修改产品行为。

必须完成：

- [x] 根级 `AGENTS.md`、`docs/PROJECT.md`、`PLANS.md` 已纳入本任务提交；
- [x] 增加必要的根级 `.gitignore`；
- [x] 通过入口、import 和调用关系确认当前主运行路径；
- [x] 确认 `MissionController`、`StateStore`、AOAdapter、Observer、Gate、Provider 和 Bus Projector 的真实关系；
- [x] 列出重复 AO Client、Observer、Gate、协议和 CLI 的实际引用；
- [x] 在本地 Python 3.12 虚拟环境中运行 v0.2 完整测试（252 项全部通过）；
- [x] 运行 `compileall` 或等价语法检查；
- [x] 运行 `run_mission.py ... --dry-run`，并将 HUMAN 结果准确分类为旧 Provider 依赖证据；
- [x] 验证 Codex CLI 使用 ChatGPT 登录，且 GPT-5.6 Sol headless probe 成功；
- [x] 记录 Python、测试、compileall、Codex probe 和 dry-run 的真实结果；
- [x] 暂存区只包含治理文件和 `.gitignore`；
- [x] 已创建面向 `main` 的 PR #1，保持未合并。

## 四、R0 真实基线

| 项目 | 结果 |
|---|---|
| 仓库基线 HEAD | `b352714`；fresh fetch 后 `main...origin/main` 为 `0 0`，任务分支基于最新 `origin/main` |
| Python | CPython `3.12.7`；本地环境 `交付/closed-loop-v2/.venv` |
| 主测试命令 | PowerShell 中设置 `PYTHONPATH=src`，将 `.venv\Scripts` 前置到 `PATH`，再运行 `.\.venv\Scripts\python.exe -m pytest .\tests -q` |
| 测试结果 | 收集 252 项：`252 passed`，32.59 s，退出码 0 |
| 测试环境结论 | 前次唯一失败由 Gate 子进程把 `python` 解析为系统解释器造成；将 `.venv\Scripts` 前置到 `PATH` 后，完整基线全部通过，无需修改产品代码或依赖 |
| compileall | `.\.venv\Scripts\python.exe -m compileall -q src panel run_mission.py`，退出码 0，0.08 s |
| Codex CLI | `codex-cli 0.150.1`；`codex login status` 返回 `Logged in using ChatGPT`；未读取或记录账号、Token、Cookie、用户配置 |
| Codex headless probe | 通过 stdin 调用 `codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol --json -`；最终 JSON 为 `{"ok":true,"probe":"codex-headless-read-only"}`，本地解析与字段校验通过，退出码 0 |
| dry-run | 使用已提交的 `tasks/mission-quick.json`；原生退出码 2，0.2 s 到达 `HUMAN`，原因是当前 headless Planner 两次拆解均调用旧 `claude` Provider 且找不到可执行文件；这是已确认的旧 Provider 依赖证据，不是安装 Claude 的环境待办。Provider 迁移完成前不要求旧 dry-run 成功 |
| 当前主入口 | `启动面板.bat → panel/server.py → run_mission.build_runtime()`；`run_mission.py → build_runtime() → run_loop()` |
| 当前唯一控制平面 | 当前代码主路径为 `MissionController`；`LoopBus` 不参与状态迁移或 Agent 指令投递 |
| 当前状态源 | CL-AO Mission/Task/预算/恢复为 SQLite `StateStore`；AO Snapshot 提供 Worker 事实；Bus、Markdown、JSONL 是后置投影 |
| 已确认重复模块 | `ao_adapter/ao_client`、`event_observer/observer`、`mission_gate/integration_gate`、`mission_contracts/protocol`、四套 CLI；详见 `docs/PROJECT.md` |
| 初始化 PR | `#1`，已通过 rebase 合并到 `main` |

R0 关闭结论：治理文件、主路径与重复模块盘点已建立；完整 pytest、compileall、
Codex ChatGPT 登录与 GPT-5.6 Sol headless probe 均已通过。旧 dry-run 失败已准确
分类为待迁移实现，不再作为 R0 阻塞，R0 因此完成。

环境或依赖阻塞时，记录原始错误并区分：

- 代码失败；
- 本地环境缺失；
- AO/模型等外部依赖未启动。

不得为了通过 R0 修改产品代码。

## 五、R1-1 验收证据

| 项目 | 结果 |
|---|---|
| 共享调用边界 | 新增 `loopcore.codex_cli.run_codex_json()`；stdin 传入 prompt，使用 `codex exec --ephemeral --sandbox read-only --model ... --output-schema ... --output-last-message ... -`，只解析临时最终消息文件并要求 JSON object；无共享层重试 |
| schema 兼容 | PlannerAction schema 明确定义可空 `replacement_task_spec.objective`；runner 派生调用期严格 transport 副本并在调用结束清理，遇到允许 object 却未声明 `properties` 的 schema 会在 subprocess 前失败；本地 validator 未绕过 |
| 生产 Planner | `CodexCliPlannerProvider` 已替换 Claude 实现；默认模型 `gpt-5.6-sol`，由 `roles.planner.model` 覆盖；`plan()` 两次失败后返回 HUMAN，`plan_decompose()` 两次失败后抛出并由 Controller 边界转 HUMAN |
| planning dry-run | `run_mission.py --dry-run` 只解析 Mission、创建 Codex Planner 并输出 MissionPlan；不组装 MissionRuntime/StateStore/AO/Worker/Auditor/Verifier/Gate/LoopBus |
| 离线测试 | `pytest tests -q`：278 项全部通过；退出码 0 |
| 语法与 diff | `compileall -q src panel run_mission.py` 与 `git diff --check` 均退出 0 |
| live Planner | `codex-cli 0.150.1`、ChatGPT 登录、`gpt-5.6-sol`；`mission-quick.json --dry-run` 最终退出 0，mission_id 匹配，生成 2 个子任务（既有范围 2..2），输出通过 structured schema 与本地 validator |
| live REPLAN | 单次真实 `plan()` probe 使用 REPLAN Audit、`remaining_replans=1` 与虚拟 session；Codex 退出 0，返回匹配 action_id/task_id 的 `REPLAN_SPAWN`，`replacement_task_spec.objective` 非空且 PlannerAction 本地 validator 通过 |
| live 副作用 | 未连接 AO、未创建 Worker、未创建或更新 runtime/state；既有 `runtime/MISSION-QUICK-001` 文件时间与 SHA-256 均保持不变 |

R1-1 关闭结论：共享 runner、Planner 迁移、planning dry-run 及 REPLAN payload
审计修复均已通过离线与真实 Codex 验证。该任务结束时 Auditor、Verifier 和 AO
Worker 尚未迁移；Auditor/Verifier 的后续迁移证据见 R1-2。

## 六、R1-2 验收证据

| 项目 | 结果 |
|---|---|
| 生产 Auditor | `CodexCliAuditorProvider` 复用 `run_codex_json()` 与现有 audit schema；保留 EvidenceBundle 截断、本地 validator、一次重试和两次失败后的 HUMAN fallback；旧类名仅为简单别名 |
| 生产 Verifier | `CodexCliVerifierProvider` 复用 `run_codex_json()` 与现有 verifier schema；保留 VerifierInput 截断、`_coerce`、本地 validator、一次重试和两次失败后的 FAIL fallback；旧类名仅为简单别名 |
| 运行时组装 | `MissionRuntime` 使用三个 Codex Provider；模型分别读取 `roles.planner.model`、`roles.auditor.model`、`roles.verifier.model`，缺省均回退 `gpt-5.6-sol`；planning dry-run 仍只构造 Planner |
| `llm_env` 边界 | 生产 `setup_environment()` 不再调用 `ensure_llm_env()`；`llm_env.py` 未删除，仅作为待 R2 审计的兼容遗留 |
| 离线测试 | `pytest tests -q`：291 项全部通过；退出码 0；其中直接相关回归 56 项全部通过 |
| 语法与 diff | `compileall -q src panel run_mission.py` 与 `git diff --check` 均退出 0 |
| live Auditor | `codex-cli 0.150.1`、ChatGPT 登录、`gpt-5.6-sol`；最小失败 EvidenceBundle 返回匹配 ID 的 `LOCAL_FIX`，本地 validator 通过，evidence 与 recommended_action 非空 |
| live Verifier | 同一 Codex 环境；含 `tests/test_x.py` 确定性路径违规的最小 VerifierInput 返回匹配 ID 的 `FAIL`，本地 validator 通过，anti-gaming 含 FAIL 项 |
| live 副作用 | 两个 probe 均使用 ephemeral/read-only；未连接 AO、未创建 Worker、未构造 StateStore，probe 期间没有 runtime 文件写入 |
| 保留边界 | Worker 仍使用旧 AO harness/model；Verifier 调用频率与 ClosedLoop/MissionController 状态机均未调整 |

R1-2 关闭结论：Auditor 与 Verifier 已迁移到共享 Codex CLI 边界，离线全测与
两个真实 Provider probe 均通过；K15 完全解决。下一独立任务为 R1-3，验证并迁移
AO Codex Worker harness/model。

## 七、R1-3 验收证据

| 项目 | 结果 |
|---|---|
| AO Desktop | Windows 安装版 `0.12.9`；内置 CLI 返回 `ao version dev`，因此产品版本以 Desktop 文件版本为准 |
| AO CLI / daemon | 使用已安装 AO Desktop 自带的 `resources/daemon/ao.exe`；公开 runfile 为 `%USERPROFILE%\.ao\running.json`，本次 daemon 端口 `3001` |
| Codex 契约 | `ao spawn --help` 明确列出 harness=`codex`、mode=`chat` 和 session 级 `--model`；`gpt-5.6-sol` 通过 `--model` 显式传递，Conversation settings 记录同一 model |
| raw AO Worker probe | 已有 `Scratch` Project 中单个 Codex Worker 成功创建，返回非空 Session ID，并精确回复 `R1-3-CODEX-WORKER-READY`；终止后 Scratch 文件树 SHA-256 与仓库 HEAD/工作区基线未变 |
| raw probe 环境边界 | 在终端 GitHub 443 不可用时，一次 Git Project 预检 spawn 返回 `SPAWN_TIMEOUT`；该空 Session 无 controller/turn/message/worktree 并已终止。成功门禁改用不依赖 GitHub 的已注册 `Scratch` Project，没有进行压力测试 |
| ActionExecutor live smoke | 临时 `StateStore` + 缺省 `TaskSpec.worker_harness` 调用 `spawn_initial_worker()`；返回非空 Session ID，Worker 精确回复 `R1-3-ACTION-EXECUTOR-ACK`，harness/mode/model 分别为 `codex`/`chat`/`gpt-5.6-sol` |
| spawn counters | ActionExecutor 成功后 `spawn_attempts`、`spawn_transient`、`spawn_next_at` 均为 `0`，`last_spawn_error` 为空；测试 Worker 已终止 |
| 代码迁移 | `TaskSpec`/`MissionSpec` 缺省 harness 为 `codex`；生产 Worker model 为 `gpt-5.6-sol`；移除显式 model 被拒后去掉 `--model` 重试的旧 GLM 特殊 fallback |
| 直接回归 | Worker contract/spawn/budget/idempotency 相关 `50 passed`，退出码 0 |
| 完整离线测试 | `pytest tests -q`：`295 passed in 32.85s`，退出码 0 |
| 语法与 diff | `compileall -q src panel run_mission.py` 与 `git diff --check` 均退出 0 |
| 保留边界 | 未运行完整 Mission；未修改 Worker 数量、Planner/Auditor/Verifier、Verifier 调用频率、状态机、Bus、Panel 或审批策略 |

R1-3 关闭结论：AO Codex Worker 已按本机公开 CLI 契约迁移到
`codex` + 显式 `--model gpt-5.6-sol`，两个成功 live smoke 与离线全测均通过；
K16 完全解决。R1 下一独立任务为 R1-4，不直接进入 R2。

## 八、R1-4 验收证据

| 项目 | 结果 |
|---|---|
| Panel Worker 契约 | R1-4 审计发现 `panel/server.py` 仍显式覆盖 `worker_harness=claude-code`；已做唯一必要的运行时一行修正为 `codex`，Panel 不硬编码 model |
| schema 契约 | `schemas/task-spec.schema.json` 的 `worker_harness.default` 已从 `claude-code` 修正为 `codex` |
| 生产默认一致性 | Planner/Auditor/Verifier 均为 headless Codex CLI、默认 `gpt-5.6-sol`；Panel/CLI、MissionSpec、TaskSpec、初始 spawn、REPLAN spawn 与 `mission-quick.json` 均为 AO `codex` harness；Worker model 由 `worker.model=gpt-5.6-sol` 注入 ActionExecutor |
| 最小回归 | 新增唯一 AST 回归 `test_panel_worker_contract.py`；Panel/Worker 相关直接回归 `16 passed in 0.96s` |
| 当前文档 | 根 README、交付说明、v2 README、`ARCHITECTURE-v0.2.md` 与 `docs/PROJECT.md` 已统一 MissionController、StateStore、AO Snapshot、角色与当前 Verifier/Worker 边界 |
| 前端拓扑 | 从全连接 Agent 通道改为以 MissionController 为中心的控制/证据流；StateStore、AO 和 Event Projection/Timeline 明确分层；没有 Auditor/Verifier/Observer → Worker 自动控制边 |
| 兼容/历史边界 | `llm_env.py`、旧 Provider 类名别名、旧 Mission JSON 与相关测试注释保留为兼容/历史证据，不进入当前默认生产组装路径，待 R2 引用审计 |
| 完整离线测试 | `pytest tests -q`：`296 passed in 31.96s`，退出码 0；比 R1-3 增加的 1 项是 Panel Worker 契约回归 |
| 语法与结构 | `compileall -q src panel run_mission.py` 退出码 0；Panel HTML 可由 stdlib parser 读取，task schema JSON 可解析且默认值断言为 `codex` |
| 文本扫描 | 当前生产入口不存在有效 Claude/GLM 默认值；当前对外 README/架构/前端不存在“不使用 Codex”、Claude/GLM 当前模型、Worker ≥2 不变量或 Bus 唯一 AO 传输层等错误事实 |
| 视觉 QA 边界 | 本地 Panel 服务可启动；当前会话无可用内置/扩展浏览器实例，因此未执行截图式浏览器视觉检查 |

R1-4 关闭结论：生产入口、schema、当前文档和前端拓扑已经统一到真实 Codex
运行契约；K1、K2、K13、K17 关闭，R1 完成。R1-4 结束时原计划下一步进入
R2-1；随后 E2E preflight 将 K18 升级为 blocker，因此先插入 R2-0。任何兼容
模块或历史来源目录仍未提前删除。

## 九、R2-0 验收证据

E2E preflight 证明 `run_mission.py` 的 AO executable、data root 和 runfile 三项
开发机 E 盘硬编码在当前机器均不存在，因此 K18 从 R4/R5 后期可移植性问题升级为
当前 E2E blocker。本任务只修主运行路径和 `auto_ff_master` 的最小导入兼容，不
开始 R2-1，也不删除重复模块。

| 项目 | 结果 |
|---|---|
| executable 解析 | `CLAO_AO_BIN` 优先，其次 `shutil.which("ao")`；两者均无时 fail fast，错误明确提示 `CLAO_AO_BIN`；不扫描磁盘、注册表或安装目录 |
| runfile 解析 | `CLAO_AO_RUN_FILE` 优先，否则使用 `Path.home() / ".ao" / "running.json"`；不再以 `AO_DATA_DIR/ao.run` 作为生产默认 |
| endpoint 与 timeout | 有效 runfile port 优先，其次显式 `ao.base_url`，最后 `http://127.0.0.1:3001`；`ao.request_timeout_seconds` 已传给 `AOAdapter` |
| 共享运行时组装 | Panel 与 CLI 继续共用 `build_runtime()`；每次构造只解析一份 `ao_bin/run_file`，同一结果传给 `AOAdapter` 与 `ActionExecutor` |
| Executor 环境 | 生产组装不再传入开发者 data root；`ActionExecutor` 不再无条件设置 `AO_DATA_DIR`，仅在明确 runfile 存在时设置 `AO_RUN_FILE` |
| Worker workspace | `AOAdapter.get_session_workspace()` 调用官方 loopback `/api/v1/desktop/sessions/{sessionId}/workspace`；缺失/空路径和 AO 404 均 fail closed，不复制 Git/Scratch layout |
| dispatch / merge | spawn 后立即解析真实 workspace 并冻结 base；merge 在 kill 前解析路径，随后 commit、创建/复用 integration、merge，不再拼 AO data root |
| integration ownership | 固定在 StateStore 同目录的 `runtime/<mission-id>/integration`；已存在有效 Git worktree 可由 final verify 直接复用，不依赖终止 Worker Session |
| `auto_ff_master` | 默认仍关闭且 Git/push 行为未重构；仅显式 `CLAO_AO_DATA_DIR` 可启用 legacy worktree 推导，未设置时明确拒绝，继续归 R4 审计 |
| 直接回归 | AO portability、runtime 组装、Panel/CLI 共享路径及既有 Worker spawn/model 回归：`42 passed` |
| PR #6 合并审计回归 | 无 AO executable 时只读 attach 可加载已有 StateStore；正常 start 仍 fail fast；相关回归 `30 passed in 0.19s` |
| 完整离线测试 | `pytest tests -q`：`308 passed in 32.18s`，退出码 0 |
| workspace API 直接回归 | AOAdapter、ClosedLoop、dispatch、merge、integration 与 final verify：`87 passed in 28.49s`，退出码 0 |
| workspace API 完整离线测试 | `pytest tests -q`：`319 passed in 42.74s`，退出码 0 |
| 语法检查 | `python -m compileall -q src panel run_mission.py`，退出码 0 |
| live portability probe | AO Desktop `0.12.9`；本机 executable 仅通过未提交的进程级 `CLAO_AO_BIN` 输入；未设置 `CLAO_AO_RUN_FILE`，默认 runfile 存在并解析到端口 `3001`；`AOAdapter.get_projects()` 成功返回 2 项；Executor 调用 `ao status --json` 退出 0、状态 `ready`；未创建 Worker |
| 路径复扫 | `run_mission.py` 已无开发机绝对路径；当前机器 executable 路径未进入 Git；旧 AO Client/CLI、`llm_env.py`、worktree 兼容逻辑和测试夹具中的抽象/合成路径保留待 R2/R4 审计 |
| workspace live probe | 未创建 Worker；本次执行时 `~/.ao/running.json` 不存在、无 AO 进程且 loopback 3001–3010 未监听，故 transport probe 连接拒绝并保持未完成，不伪造成功证据 |

R2-0 准确结论：K18 的主生产运行路径已解决；AO executable、runfile 与 Worker
workspace 均已移除开发者绝对路径或内部目录推导绑定。这不等于 K18 所涉及的
全部用户交付可移植性已经完成。clean clone bootstrap/安装脚本
归 clean-delivery，AO 首次配置 UX 归比赛 UX/clean-delivery，Project 注册/选择归
比赛 UX/R4，`auto_ff_master` legacy data root 归 Competition convergence/R4。
当前下一步是 demo bootstrap + GUI E2E，随后优先做比赛行为收敛，不直接开始 R2-1。

### 第一次真实 GUI E2E 与语义角色恢复

`MISSION-PANEL-20260901-140528` 已真实跑通 Panel → Planner → AO Codex Worker
（harness=`codex`、model=`gpt-5.6-sol`）→ AO official Session workspace API →
Observer。Worker 最终正确实现 `clamp01_e2e`，自身验收命令退出 0，只修改
`app.py` 并回复 DONE，因此本次终局不得分类为 Worker implementation failure。

该次运行确认两个最早 blocker：

1. Worker 的 AO turn 仍为 active/reconnecting 时，三个同 fingerprint provider
   error 被 Observer 正确记录为 `REPEATED_ERROR`，但 Controller 立即进入
   `AUDIT_PENDING`，导致语义审计捕获到编辑完成前的红 Gate 证据；
2. Auditor 的两次 120 秒 Codex transport failure 被 Provider 构造成 semantic
   `HUMAN`（`auditor_format_failure`），Planner 随后合法执行该错误业务结论。

当前最小修复保持 Observer 与 StateStore 事实不变：active turn 的
`REPEATED_ERROR` 只记录、不触发语义干预；完成后仍走现有 completion audit，读取
最新 workspace/diff/Gate evidence。Auditor/Verifier 的 transport failure 立即抛给
现有 Controller step boundary；schema-invalid 只在 Provider 内重试一次，第二次
仍失败则抛 provider protocol error；合法 semantic `HUMAN`/`FAIL` 保持原语义。
三个 Codex role 的生产 timeout 统一为 180 秒。现有 bounded retry 连续三次失败
才转 `consecutive loop errors` HUMAN，不新增 retry verdict、状态、队列或数据表。
直接相关回归 `61 passed in 17.76s`；完整离线基线
`326 passed in 40.09s`；`compileall` 与 `git diff --check` 均退出 0。本节只记录
已发生的 E2E 与已实现/离线验证边界；修复后的 GUI E2E 尚待本 PR 合并后重跑。

## 十、已知问题清单

| 编号 | 问题 | 计划阶段 | 状态 |
|---|---|---|---|
| K1 | 旧架构文档与代码主路径不一致 | R1 | 已解决：当前 README、交付说明、架构文档、PROJECT 和前端均与真实主路径一致 |
| K2 | Loop Bus 文档职责与 Bus Projector 实际职责不一致 | R1 | 已解决：当前文档和 UI 明确 Bus 是 Store 后置事件投影，不是控制或 AO 指令路径 |
| K3 | 多套 AO Client、Observer、Gate、协议与 CLI | R2 | 已确认：主路径与兼容/历史模块同时存在 |
| K4 | `clao-src`、sidecar 与主产品同时交付，边界不清 | R2 | 已确认：三者同时交付；主路径无跨目录 import，来源目录当前仅作参考 |
| K5 | 默认强制拆成至少两个 Worker | R3 | 已确认：面板和示例默认 `max_subtasks=2`，Planner 提示要求 `2..max` |
| K6 | Verifier 使用过重且旧文档允许绕过 Planner | R3 | 已确认：当前每个子任务和 Mission 终局都调用 Verifier；实际结果回 Controller/Planner 路径 |
| K7 | issue fingerprint 包含 source | R3 | 已确认：`issue_fingerprint()` 返回值显式包含 `source` |
| K8 | thread 缺少 revision 裁决语义 | R3 | 已确认：同一 issue 只允许一次 verdict，没有 revision 字段或重裁决路径 |
| K9 | 多套状态与投影没有明确主从 | R1/R2 | 已解决：代码与当前文档均明确 StateStore/AO Worker 事实与后置投影关系；R2 只处理重复实现 |
| K10 | 配置项重复、未接线或 UI/后端语义不同 | R4 | 部分解决：R2-0 已接入 `ao.base_url` 与 `ao.request_timeout_seconds`；`roles.*`、`roles.max_parallel_workers` 等其余配置仍待 R4 收敛 |
| K11 | 面板偏向 bundled demo，缺少真实 Project 选择 | R4 | 已确认：项目缺省/回退均为 `closed-loop-demo`，没有 AO Project 列表选择路径 |
| K12 | 自动审批和自动 push 边界过宽 | R4 | 已确认：自动审批已接线；`auto_ff_master` 默认关闭但可由面板 API 开启并 push |
| K13 | 测试数量与冻结状态文档不一致 | R0/R1 | 已解决：清理永久冻结数字；R1-3 main 基线为 295，R1-4 实跑 296，以后以 CI/当前输出为准 |
| K15 | 当前 Planner/Auditor/Verifier 与 `llm_env` 绑定 Claude CLI、`ANTHROPIC_MODEL` 和 `GLM-5.2` | R1 | 已解决：三个生产 Provider 均复用 Codex CLI，生产组装不再调用 `ensure_llm_env()`，默认模型均为可配置的 `gpt-5.6-sol` |
| K16 | 当前 Worker 默认 `worker_harness=claude-code`、`worker.model=GLM-5.2` | R1 | 已解决：Panel/CLI、MissionSpec、TaskSpec、schema、初始与 REPLAN spawn 均为 `codex`，生产 model 为显式 `gpt-5.6-sol`，raw AO 与 ActionExecutor smoke 均通过 |
| K17 | 旧 README、`ARCHITECTURE-v0.2.md` 和 `default.yaml` 明确写有“不使用 Codex”或 Claude/GLM 依赖 | R1 | 已解决：当前生产配置、README、架构说明和前端均统一为 Codex 契约；兼容/历史字符串明确不属于生产路径 |
| K18 | 主生产路径和用户交付可移植性 | R2-0/比赛 UX/R4/R5 | 主生产运行路径已解决：AO executable、runfile、Worker workspace 已移除开发者绝对路径/内部 layout 推导。仍未解决：clean clone bootstrap/安装脚本、AO 首次配置 UX、Project 注册/选择、`auto_ff_master` legacy data root；不得宣称为通用安装包 |

## 十一、阶段边界

### R1

按独立小任务迁移 Provider 并统一事实与展示，不做一次性大重构或大规模删除。
R1-1 已迁移 Planner 并恢复 dry-run，R1-2 已迁移 Auditor/Verifier，R1-3 已依据
本机 live probe 迁移 AO Codex Worker harness/model，R1-4 已统一 Panel、schema、
当前架构文档、README 和前端拓扑。R1 已完成，结果为：

- `MissionController` 唯一控制平面；
- `StateStore` 唯一 CL-AO 状态源；
- Bus 改为 Event Projection；
- 前端拓扑区分逻辑角色与真实物理调用；
- 当前 README、架构文档与前端展示一致；兼容/历史代码注释保留并明确分类；
- Planner/Auditor/Verifier 共享一个 ephemeral、read-only、结构化输出的 Codex CLI 调用边界；
- Worker 使用经本机 live probe 验证的 AO Codex harness/model 参数。

### R2

R2-0 已修复真实 E2E preflight 暴露的 AO executable/runfile blocker，并在本
workspace API PR 中以 AO 官方 loopback endpoint 取代 Worker workspace 内部目录
推导。重复实现清理不再作为 E2E 后的第一任务；待 Competition behavior
convergence 完成后再开始 R2-1。删除前仍必须有测试和入口证据。

### R3

完整 E2E 后优先做 Competition behavior convergence：

- Worker 默认 1，最多 2；
- Verifier 默认 final/终局，高风险时可选，不再每个子任务默认调用；
- 隐藏或显式标记 `auto_ff_master` 为实验性高风险功能；
- 当前 `ClosedLoop` 仍有 bounded L0 direct worker nudge；R3 决定保留该
  fast path，还是将自动 Worker 指令统一路由 Planner；
- fingerprint 去 source 与 thread revision 支持多轮新证据继续低优先级，
  不阻塞比赛行为收敛。

### R4

收敛产品化边界：

- 项目选择；
- 生效配置；
- 人工 override；
- 审批白名单；
- 自动 push/merge 默认关闭或移除。

### R5

完成：

- CI；
- 全新 clone 安装；
- AO 官方依赖说明；
- 不携带 AO 用户数据；
- 通用项目与 Demo 模式；
- 最终比赛彩排和干净源码包。

当前顺序固定为：workspace API PR → demo bootstrap + GUI E2E → Competition behavior
convergence → 重复模块清理 → clean delivery/installer/first-run。R1-1、R1-2、
R1-3、R1-4 与 R2-0 主体已完成；本轮不启动 E2E、Worker/Verifier 策略调整或
R2 删除。

## 十二、停止条件

出现以下任一情况立即停止当前任务并报告：

- 工作区存在无法解释的预先改动；
- 当前分支或远端历史与任务假设不一致；
- 需要修改任务允许范围之外的文件；
- 测试依赖要求修改产品依赖文件；
- 发现真实凭据、AO 用户数据或隐私内容；
- 现有文档与代码冲突且无法由只读检查判断；
- push 或 PR 创建失败且常规重试仍无法解决。
