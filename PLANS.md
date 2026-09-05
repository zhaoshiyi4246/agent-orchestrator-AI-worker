# v0.2 修正计划

- 当前阶段：R5 complete
- 当前任务：R5-5 Final Closeout Evidence
- 当前状态：R5 COMPLETE；clean release、Final CLI live 与人工 GUI live 均已 PASS，目标仓库 main/origin 未被自动写回或 push。
- 下一步：Final Release Closeout Build

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
| R2 | AO 主路径可移植性；重复模块、旧入口和参考代码收敛 | 已完成 |
| R3 | Competition behavior convergence：Worker、Verifier、自动 SCM 边界；issue/thread 低优先级 | 主要 competition 路径已完成；低优先级治理项保留 |
| R4 | 配置有效性、项目选择和高风险功能收敛 | 已完成（Project selector；GUI smoke PASS） |
| R5 | CI、全新安装、真实 Demo 与干净交付 | 已完成（Final CLI/GUI live PASS） |

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
| `auto_ff_master` | R2-0 当时仍默认关闭且未重构；该历史边界已由 R3 #4 删除，见后文当前证据 |
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
比赛 UX/R4；R2-0 当时保留的 `auto_ff_master` legacy data root 后由 R3 #4 删除。
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

### 第二次真实 GUI E2E 与 Worker materialization commit recovery

`MISSION-PANEL-20260901-160239` 已真实验证 Panel → Planner → AO Worker →
completion audit → Planner → Task Gate → Task Verifier → Task DONE。Worker workspace
中的 `app.py` 实现正确且 `git add` 成功；其后的 trusted sidecar materialization
`git commit` 返回 nonzero，使 Mission 在 integration 前 fail closed 到 `HUMAN`。

原始 commit failure 的精确根因是 **UNKNOWN**：当时 `commit_all()` 丢弃 stderr，
后续只读检查不能复现；identity、signing、hook、lock、diff 与 permission 均未发现
异常，当前 `git commit --dry-run` 成功。因此本任务不得把该事件记录为
identity/GPG/hook/lock bug，也不针对这些未经证明的原因改写 Git policy。

当前最小修复保持 materialization 为确定性 Git 操作：无改动返回当前 HEAD；有改动
时最多执行 2 次完整 add/commit，第一次瞬时失败后仅短暂等待一次；第二次仍失败则
抛出包含最后一次有界 Git stdout/stderr 的 stage-specific 异常。Mission 不增加第二
层 retry，persistent failure 直接以真实 Git detail 转 `HUMAN`，integration 不创建、
merged 保持为空。该路径不写 Git config、不使用 `--no-verify`，也不改变用户 hook
或 signing policy。完整离线基线为 `336 passed in 293.08s`；`compileall` 与
`git diff --check` 均退出 0。第三次真实 GUI E2E 尚待本 PR 审计合并后运行。

### 第三次真实 GUI E2E 与 exact-path materialization

`MISSION-PANEL-20260901-200228` 再次真实验证 Panel → Planner → AO Worker →
completion audit → Planner → Task Gate → Task Verifier → Task DONE。Worker 正确实现
`clamp01_e2e`，修改已 staged，Task Gate 与 Task Verifier 均 PASS；Mission 在创建
integration 前因 materialization `git add` persistent failure 转 `HUMAN`。

PR #9 已正确执行两次有界 materialization attempt，并将最后一次真实 stderr 写入
Mission reason，因此本次根因可以明确更新为
`DETERMINISTIC_GIT_ADD_ARTIFACT_PATHSPEC_BUG`：`commit_all()` 在已经由
`changed_paths()` 过滤 artifact 后，仍执行 `git add -A -- .` 加显式 artifact
exclusion pathspec；真实 worktree 同时存在 ignored `__pycache__` 时，Git 以
ignored-path error nonzero。两次 retry 均执行了同一确定性错误命令，故不能恢复；
这不是瞬时 Git fault。

当前最小修复只 stage `changed_paths()` 返回的真实非 artifact 路径，并使用 literal
exact pathspec；不扫描 `.`、不将 ignored artifact 传给 `git add`、不使用 `-f`，
也不修改 `.gitignore`、`.git/info/exclude` 或 Git config。PR #9 的两次上限 retry、
0.5 秒等待、stderr preservation 与 persistent `RuntimeError` 全部保留。直接相关
回归 24 项全部通过；完整离线基线 `342 passed in 50.80s`；单独的
`--durations=20` 完整运行 `342 passed in 50.38s`，最慢项为 fake Mission merge
`5.05s`，本任务未顺带优化测试性能。

### 首次完整 GUI happy path 与 Task Verifier final-only

`MISSION-PANEL-20260901-214216` 首次真实跑通 Planner decomposition → AO Worker →
Completion Auditor → Planner → Task Gate → Task Verifier → Task DONE → materialization →
integration → Final Gate → Mission Verifier → `MISSION_DONE`；最终原因为
`final gate pass + verifier PASS`，总耗时约 `776.9s`。其中 Task Verifier 约 `125s`，
Mission Verifier 约 `130s`，证明普通子任务默认复核存在明确重复成本。

本次最小收敛只改变新 Task Gate PASS 的目标状态：`GATE_PENDING → DONE`，不调用
Task Verifier、不生成 task-level verification row。Gate FAIL 仍进入原有
`AUDIT_PENDING → Auditor → Planner` 路径。`VERIFIER_PENDING` 状态和 verifier 实现
均未删除；历史 runtime 恢复时继续执行旧 task verifier，semantic FAIL、coherence
retry、provider retry、budget 与 crash-resume 语义保持。Mission Final Gate 与
Mission Verifier 不变，完整 fake Mission 证明 Task Verifier 为 0、Mission Verifier
为 1、最终仍为 `MISSION_DONE`，StateStore 仅写 mission-level verification row。

直接相关回归为 `47 passed in 72.12s`。完整离线基线首次运行
`343 passed in 152.71s`；因明显慢于近期约 50 秒基线，按要求单独补跑
`--durations=20`，结果为 `343 passed in 81.41s`，最慢项仍为 fake Mission merge
与 final-gate/crash-resume 类测试（最慢 `10.51s`）。`compileall`、
`git diff --check` 与修改文档的新增 Markdown 链接扫描均退出 0；本任务不优化
测试性能。

### PR #11 性能 E2E 与 gate-first happy path

PR #11 final-only 合并后的同题真实性能 E2E `MISSION-PANEL-20260902-000139`
到达 `MISSION_DONE`，总耗时 `646.116s`；相对旧基线
`MISSION-PANEL-20260901-214216` 的 `776.897s` 节省 `130.781s / 16.83%`。
该次真实运行已验证 Task Verifier 为 0、Mission Verifier 为 1、
`GATE_PENDING → DONE` 与 Mission Final Gate/Verifier 均正确；剩余普通 Task
happy path 的 Completion Auditor 与 completion Planner 分别约为 `125s` 和
`122s`。

本次 #2 最小收敛只优化首次 `WORKER_RUNNING` completion。Worker 必须明确处于
idle/waiting_input/needs_input/exited/terminated，且没有 pending approval、本 tick
的 actionable Observer alert 或需要 L0 nudge 的 fresh error；Task 至少有一个非空 Gate
命令；AO workspace 可解析；Git `changed_paths` 可审计且至少包含一个 non-artifact
change。全部满足时执行 `WORKER_RUNNING → GATE_PENDING → _run_gate()`：Gate PASS
直接 DONE，Completion Auditor、completion Planner 与 Task Verifier 调用均为 0；
Gate FAIL 保持 `GATE_PENDING → AUDIT_PENDING → Auditor → Planner`。

空 Gate、`changed_paths == []`、`changed_paths == None`、workspace/base 不可审计或
其他任一条件不足都继续 Completion Audit。本次没有改变 `WORKER_RETRYING`
completion、actionable alert、active-turn `REPEATED_ERROR` 延迟、L0 nudge、Mission
Final Gate/Verifier、historical `VERIFIER_PENDING`、Worker 数量、`auto_ff_master`、
Panel UI 或 Planner decomposition。

新增 gate-first 定向回归 `11 passed in 12.35s`；包含审批、alert/L0、retry、
historical verifier 与完整 fake Mission 的直接回归为 `60 passed in 43.42s`；完整
离线基线为 `354 passed in 53.41s`。完整 fake Mission 通过真实 `ClosedLoop.step()`
证明 clean Task Auditor 为 0、completion Planner 为 0、Task Verifier 为 0，Mission
Verifier 为 1，最终为 `MISSION_DONE`。`compileall` 退出码为 0。本轮按要求未运行
真实 GUI E2E。`git diff --check` 与 6 份修改文档的本地 Markdown 链接扫描均
退出 0（3 个本地链接存在，missing 为 0）。

### Mission shared-routing event freshness

真实 Mission `MISSION-PANEL-20260902-115314` 在 Worker idle、无 approval、无 actionable
alert、Gate 非空、workspace/base 可审计且 `changed_paths=["app.py"]` 时，
仍未命中 gate-first。根因是 Mission 每 tick 从 `since=0` 取得 AO
replay/full-history snapshot，shared routing 未应用已有的 per-worker activity cursor；
重放的历史 error 又被 `ClosedLoop.step()` 直接放入 `fresh_errors`，从而形成
pending L0，阻断 gate-first 并额外调用 Completion Auditor 与 Planner。

当前最小修复保留每 project 每 tick 一次 AO API 调用，仍以 `since=0`
读取 snapshot。`MissionController._route_events()` 复用
`loop._event_since[worker_session_id]`：Session/turn 正常 normalize，activity 仅在
`sequence > cursor` 时 normalize，且只由所属 Worker 推进自己的 cursor。
多 Worker 的 sequence 互不污染；REPLAN 新 Worker 的 session id 可从 sequence 1
开始，不继承旧 Worker cursor。

`ClosedLoop.step()` 在 `Observer.feed()` 前检查持久化
`StateStore.event_seen(event_id)`；只有未处理的 activity error 才是
`fresh_errors`。Observer 继续独占 event 持久化和 alert dedup 权威，没有复制
fingerprint/alert 逻辑。因此同进程 replay 由 per-worker cursor 过滤，
crash/restart 后内存 cursor 丢失则由 persistent `event_id` 去重兜底。新回归证明
历史 seq 2/3/4 不创建 L0 `hatched_at`，`allow_gate_first=True`，Task 以
`WORKER_RUNNING → GATE_PENDING → DONE` 完成，Completion Auditor 与 completion
Planner 均为 0；崩溃后新 `ClosedLoop` 注入相同历史 error 也可 gate-first。

新增 5 项回归覆盖真实两 tick 重放、Session/turn 保留与 activity 过滤、
多 Worker cursor 隔离、REPLAN 新 Worker 低 sequence 和 crash/restart 持久化去重。
相关 event/Observer/crash-resume/gate-first/Mission 定向回归为
`54 passed in 13.53s`。
完整离线基线 `python -m pytest tests -q` 为
`359 passed in 47.54s`。首次完整运行暴露了新回归夹具的零 alert cooldown
与真实前提不一致（`358 passed, 1 failed`）：idle Session 作为真正新事件
合法产生了 actionable alert。回归改用生产 600 秒 repeated-error cooldown 以
表达“tick 2 无新 actionable alert”的前提；产品 Observer/alert 语义未修改。
`python -m compileall -q src panel run_mission.py` 与 `git diff --check` 均退出 0；
本轮按要求未运行真实 GUI E2E。

### Default single Worker

新 Mission 的 `MissionSpec` 缺省与 Panel 默认均已改为 `max_subtasks=1`；Panel
只接受 1 或 2，对 0、负数和大于 2 的值返回明确错误，不再用 truthy fallback
静默 clamp。首次分解时，1 由 `MissionController` 确定性生成唯一
`<mission-id>-S1` 标准 MissionPlan，完整继承 objective、allowed paths、验收条件
和 Gate；TaskSpec materialization 继续继承 forbidden paths、user instruction、
budgets、worker harness 和 `subtask_of`。该路径的 decomposition Planner 调用为 0。

只有 `max_subtasks=2` 才调用 `Planner.plan_decompose()`。Planner prompt 与本地
validator 现允许返回 1 或 2，默认优先 1；只有路径、验收和依赖可自然独立且存在
真实并行收益时才使用第二 Worker。返回超过 2 个 task 会被 validator 拒绝。新
Mission 的其它上限在首次分解时也明确转 HUMAN，不静默降级。配置中的
`roles.max_parallel_workers=2` 当前没有运行时 consumer，保留为能力上限。

恢复仍先从 StateStore hydrate 已持久化的标准 MissionPlan；2-task 与历史 3-task
计划均不会应用新建上限或重新 decomposition。新增 `tasks/e2e-smoke.json` 作为今后
标准 GUI E2E 的固定输入，本 PR 不自动执行真实 AO Worker/GUI E2E，并保留原
`tasks/mission-quick.json` 不改。直接相关回归为 `58 passed in 24.47s`。完整离线
基线首次为 `375 passed in 142.67s`；因显著慢于近期基线，按要求单独补跑
`--durations=20`，结果为 `375 passed in 129.48s`。最慢项仍集中在 fake Mission、
worktree 与 Verifier 类测试；本次新增的 single-lane fake Mission 为 `9.37s`，未
顺手优化测试性能。`python -m compileall -q src panel run_mission.py`、
`git diff --check`、fixture 契约检查与 6 份指定文档的本地链接检查均退出 0。

审计合并后的标准 smoke `MISSION-E2E-SMOKE-20260902-204459` 真实到达
`MISSION_DONE`：确定性单任务计划，decomposition Planner、Completion Auditor、
completion Planner 与 Task Verifier 调用均为 0，Worker 为 1，Mission Verifier 为
1；demo master 保持不变，总耗时约 `409.5s`。因此核心 single-worker happy path
停止继续优化，后续回到比赛产品安全边界主线。

### Disable automatic master push

Competition Panel 已直接删除普通 UI 中的自动写回 checkbox、tooltip、snapshot
同步与 config POST 字段；HTML 不再包含 `k_ff`、`auto_ff_master` 或“DONE 后自动
合并 master”。PanelState 不再保存该状态，snapshot/config 不再将其作为可调参数
暴露，`MISSION_DONE` 只生成终局 summary，不调用 SCM helper。

旧客户端发送精确 legacy `auto_ff_master=false` 时该字段被忽略，其它时间参数正常
应用；任何非 `false` 值（包括 `true`）都会在应用其它更新前以
`auto_ff_master is disabled in the competition runtime` 明确拒绝。引用与 AST 审计
证明 `ff_master_to_integration()` 在删除完成分支后无生产调用者，因此 helper、
专用 `subprocess` import 与旧 data-root 推导一并删除，没有迁移到
`runtime/<mission-id>/integration`。

`CLAO_AO_DATA_DIR` 已无当前 v0.2 正常生产消费者。旧 AO Client/CLI 和仍依赖
`AO_DATA_DIR` 的兼容代码/夹具属于 R2 cleanup，本 PR 不顺手删除。Panel 定向回归
`33 passed in 0.42s`；包含 single-worker、gate-first 与 final verifier 的直接回归
`53 passed in 41.77s`；完整离线基线 `python -m pytest tests -q` 为
`380 passed in 117.70s`。`python -m compileall -q src panel run_mission.py`、
`git diff --check`、Panel/生产 consumer 文本扫描与 6 份指定文档的本地链接检查
均退出 0。本任务不运行真实 AO Worker/E2E。

### R4 Project selector

Panel 新增只读 `GET /api/projects`：通过现有 `AOAdapter.get_projects()` 调用 AO
官方 `/api/v1/projects`，只返回 `id/name/path/kind`。构造 Adapter 时复用
`run_mission.load_config()`、`resolve_ao_run_file()` 以及正常 runtime 的 base URL、
request timeout 与 runfile；不读取 `ao.db`、`AO_DATA_DIR` 或 AO worktree 根目录。
AO 不可用时返回 `ok=false` 与真实错误，不构造 `closed-loop-demo`。

新建 Mission 表单在 Panel 启动和打开时加载 Project，可手动刷新，默认明确选中
第一项并显示只读 path/kind；0 项或 API 错误时显示原因并禁用启动。浏览器只把
selector 的 `project_id` 与原有 Mission 字段一起 POST。后端启动时再次读取 AO
registry，拒绝缺失/未知 ID、空 path、path 不存在或不是目录的项目；全部验证都在
写入任务文件与 `PANEL.start_mission()` 前完成。生产代码中的
`body.get("project_id") or "closed-loop-demo"` 已删除，不自动选择、创建、注册或
修改 Project。

历史 Mission 的查看/resume 继续直接使用 StateStore 中已持久化的 Mission
payload，不查询或应用当前 selector；CLI 继续通过 Mission JSON 显式提供
`project_id`，语义未改。Panel 定向回归为 `25 passed in 0.76s`；完整离线基线
`python -m pytest tests -q` 为 `390 passed in 67.60s`；
`python -m compileall -q src panel run_mission.py`、`git diff --check` 均退出 0；
6 份指定文档的本地 Markdown 链接检查共检查 3 个链接，missing 为 0。本任务按
要求未运行真实 AO Worker/GUI E2E。后续真实 AO/Panel Project selector GUI smoke
已 PASS，R4 Project selector 因此在阶段总览中标记为已完成。

## 十、已知问题清单

| 编号 | 问题 | 计划阶段 | 状态 |
|---|---|---|---|
| K1 | 旧架构文档与代码主路径不一致 | R1 | 已解决：当前 README、交付说明、架构文档、PROJECT 和前端均与真实主路径一致 |
| K2 | Loop Bus 文档职责与 Bus Projector 实际职责不一致 | R1 | 已解决：当前文档和 UI 明确 Bus 是 Store 后置事件投影，不是控制或 AO 指令路径 |
| K3 | 多套 AO Client、Observer、Gate、协议与 CLI | R2 | RESOLVED：三套 legacy CLI、旧 AO Chat protocol、AOClient/old Observer island 与旧 `integration_gate.py` 均已退休；当前 v2 只保留正式边界 |
| K4 | `clao-src`、sidecar 与主产品同时交付，边界不清 | R2/R5 | RESOLVED：source boundary 与 package boundary 均已收敛；allowlist release 只生成顶层 `clao/` 产品，历史来源不进入 artifact |
| K5 | 默认强制拆成至少两个 Worker | R3 | 已解决：新 Mission 默认 1；值为 1 时确定性单 lane 且不调用 decomposition Planner；显式选择 2 时 Planner 可返回 1 或 2 |
| K6 | Verifier 使用过重且旧文档允许绕过 Planner | R3 | 第一阶段已解决：新 Task Gate PASS 直接 DONE，Task Verifier 默认调用为 0；历史 `VERIFIER_PENDING` 可恢复，Mission Final Verifier 仍调用 1 次；高风险子任务显式按需策略未新增 |
| K7 | issue fingerprint 包含 source | R3 | 已确认：`issue_fingerprint()` 返回值显式包含 `source` |
| K8 | thread 缺少 revision 裁决语义 | R3 | 已确认：同一 issue 只允许一次 verdict，没有 revision 字段或重裁决路径 |
| K9 | 多套状态与投影没有明确主从 | R1/R2 | 已解决：代码与当前文档均明确 StateStore/AO Worker 事实与后置投影关系；R2 只处理重复实现 |
| K10 | 配置项重复、未接线或 UI/后端语义不同 | R4 | 部分解决：R2-0 已接入 `ao.base_url` 与 `ao.request_timeout_seconds`；`roles.*`、`roles.max_parallel_workers` 等其余配置仍待 R4 收敛 |
| K11 | 面板偏向 bundled demo，缺少真实 Project 选择 | R4 | 已解决：Panel 从 AO 官方 registry 读取 Project，新建 Mission 显式选择并在启动前重验 ID/path；`closed-loop-demo` 隐式 fallback 已删除 |
| K12 | 自动审批和自动 push 边界过宽 | R3/R4 | 部分解决：competition Panel 已删除自动 master/main merge 与 origin push；自动审批仍待 R4 审计 |
| K13 | 测试数量与冻结状态文档不一致 | R0/R1 | 已解决：清理永久冻结数字；R1-3 main 基线为 295，R1-4 实跑 296，以后以 CI/当前输出为准 |
| K15 | 当前 Planner/Auditor/Verifier 与 `llm_env` 绑定 Claude CLI、`ANTHROPIC_MODEL` 和 `GLM-5.2` | R1 | 已解决：三个生产 Provider 均复用 Codex CLI，生产组装不再调用 `ensure_llm_env()`，默认模型均为可配置的 `gpt-5.6-sol` |
| K16 | 当前 Worker 默认 `worker_harness=claude-code`、`worker.model=GLM-5.2` | R1 | 已解决：Panel/CLI、MissionSpec、TaskSpec、schema、初始与 REPLAN spawn 均为 `codex`，生产 model 为显式 `gpt-5.6-sol`，raw AO 与 ActionExecutor smoke 均通过 |
| K17 | 旧 README、`ARCHITECTURE-v0.2.md` 和 `default.yaml` 明确写有“不使用 Codex”或 Claude/GLM 依赖 | R1 | 已解决：当前生产配置、README、架构说明和前端均统一为 Codex 契约；兼容/历史字符串明确不属于生产路径 |
| K18 | 主生产路径和用户交付可移植性 | R2-0/比赛 UX/R4/R5 | RESOLVED：portable AO boundary、Project selector、Python bootstrap、shared Mission preflight、clean artifact builder 与 standalone artifact CLI/GUI live 均已验证；Project 注册仍按产品契约由外部 AO 负责 |

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
推导。Competition behavior 主路径和 Project selector 完成后，当前工作已切回
duplicate / legacy convergence。删除前仍必须有测试和入口证据。

#### R2-1 Reference Graph Audit、Legacy Retirement 与 Gate Integrity Migration

Reference Graph Audit 已完成并确认 `llm_env.py` 从 `run_mission.py`、
`panel/server.py` 与 Controller production roots 不可达；生产 Planner、Auditor、
Verifier 只复用 `codex_cli.run_codex_json()`，不需要 Claude CLI、GLM gateway、
`ANTHROPIC_MODEL` 或 `CLAUDE_CODE_GIT_BASH_PATH`。

Batch 1 只删除 `src/loopcore/llm_env.py` 及其 legacy contract 测试，不复制
`run_claude`、`_kill_process_tree`、`ensure_llm_env` 或 `find_git_bash` 到
`codex_cli.py`。Auditor/Verifier 不设置 `ANTHROPIC_MODEL` 的 current invariant 已分别
迁入对应 Provider 测试；Planner 的同类测试沿用既有覆盖。Auditor 与 Verifier 定向
测试各 `8 passed`，完整离线基线为 `388 passed in 80.23s`，`compileall` 退出码为 0。
本任务不运行 AO、Codex live probe、Mission 或 E2E，也不处理其它 legacy 模块。

Legacy CLI Retirement Audit 已确认 `mission_cli.py` 与 `closed_loop_cli.py` 从
Panel、`run_mission.py` 和 Controller production roots 不可达，也没有测试消费者。
Batch 2A 只删除这两个 leaf legacy entrypoint；不迁移 `_wire_jsonl`、独立
ClosedLoop runner、`AO_DATA_DIR`、bundled AO path、`--worker-session` 或 legacy
`--instruct`。`cli.py` 及其 `test_watch_fresh_only_once.py` 明确保留给独立 Batch 2B，
`protocol.py` 保留给独立 contract retirement batch。

本批在现有 Panel/entrypoint 测试中增加 1 项最小静态回归，验证两个 legacy source
不存在、`run_mission.py` 与 `panel/server.py` 仍存在，并禁止恢复已删除 CLI 仍是
兼容入口的 stale claim。定向测试为 `26 passed in 0.16s`，完整离线基线为
`389 passed in 95.90s`；`python -m compileall -q src panel run_mission.py` 与
`git diff --check` 均退出 0。当前 production source/Panel/runner 对
`mission_cli`、`closed_loop_cli`、`_wire_jsonl` 的引用为 0；历史来源目录未修改。

Batch 2B 只删除 `src/loopcore/cli.py` 与它的专用 legacy 测试
`tests/sidecar_port/test_watch_fresh_only_once.py`。Snapshot、`--once`/`--watch`、
SSE、`--fresh` 和旧 events/alerts JSONL writer 均不迁移；当前正式 event freshness
继续由 gate-first/shared routing、per-worker cursor、持久化 `event_seen` 与 Bus
projector high-water/idempotency 覆盖。entrypoint 静态回归扩展为要求三套 legacy
CLI source 均不存在，并只依赖正式入口声明而不逐字绑定新的退休说明。下一步单独
处理 `protocol.py` contract retirement。Batch 2B 的 entrypoint 定向回归 26 项、
完整离线 387 项、compileall 与 `git diff --check` 均通过。

Protocol Retirement Audit 已确认 legacy v2 `src/loopcore/protocol.py` 没有
production/test、schema、prompt、fixture 或当前公开兼容消费者。当前
Planner/Auditor/Verifier 使用 headless Codex CLI Provider，通过 Python objects 与
JSON schemas 同 Controller 交互，不通过 AO Chat 交换旧 camelCase DTO。本批仅删除
该 v2 source，不增加 compatibility shim、re-export、wrapper、alias 或 DTO converter；
`clao-src` 自己的历史 `protocol.py` 与 callers 保持不变。`integration_gate.py`
docstring 中的 `AuditRequest` 是明确 deferred legacy hit，留待旧 Gate 独立审计。
完整离线测试为 `387 passed in 72.99s`；compileall 与 `git diff --check` 均退出
0。下一步进入 AO Client / old Observer island audit。

AOClient / old Observer Island Audit 已审计 PASS：legacy v2
`src/loopcore/ao_client.py` 与 `src/loopcore/observer.py` 仅形成互相连接的 leaf
island，无 current production caller、current tests 或 current public contract。本批
删除两个 source；不迁移 `check_health`、httpx client、strict workspace snapshot、
message-revision progress、`REPEATED_FAILURE`、`MILESTONE` 或 `STALL`，也不增加
compatibility shim。当前 AO 读写继续分别由 `AOAdapter` 与 `ActionExecutor` 负责，
当前确定性告警继续由 `event_observer.Observer` 负责；`clao-src` 与
`ao-supervision-sidecar` 的历史副本和测试不修改。下一步独立审计旧
`integration_gate.py`。当前边界相关定向回归为 `48 passed in 22.65s`，完整离线
基线为 `387 passed in 120.29s`；compileall 与 `git diff --check` 均退出 0。

旧 Integration Gate retirement audit 已审计 PASS，结论为
`MIGRATE_ONE_REQUIRED_SAFETY_PROPERTY_THEN_RETIRE`。审计确认 legacy v2
`integration_gate.py` 无 current production/test/public-contract caller，同时发现当前
`mission_gate.py` 的 `CURRENT_GAP`：HEAD probe failure 可被吞掉，且 Gate 命令可在
exit 0 时改变 index、tracked/untracked 内容或 HEAD 而仍被视为通过。

本批只迁移 Gate repository integrity。`worktree.py` 提供只读、内容敏感 snapshot，
覆盖 HEAD、完整 cached/unstaged diff 摘要，以及 non-artifact untracked path 与内容
hash，并复用既有 artifact 语义。Task/Completion Gate 允许 initial dirty，但前后状态
必须一致；Final Gate 要求 initial clean。所有必要 Git/file probe failure 均 fail
closed；Final integrity failure 直接进入 `HUMAN` 并跳过 Mission Verifier。Gate 命令
失败的既有 baseline-only tolerance 仅在 integrity PASS 时保留。旧 Gate 的逐命令
probe、`IntegrationGateResult`/`GateStepResult` DTO 与字符串 evidence 协议不迁移。
新回归通过后已删除 legacy v2 `integration_gate.py`，不增加 shim/alias/re-export，且
不修改 `clao-src` 或 `ao-supervision-sidecar` 历史来源。Gate 定向回归为
`61 passed in 47.18s`，完整离线基线为 `404 passed in 74.52s`；compileall、
`git diff --check` 与 current production/tests legacy reference scan 均通过。下一步为
R2 closure audit。

R2 Closure Audit 已 PASS：current production authority 已收敛为单一
AO/Observer/Gate/Contract/CLI 边界，已退休 legacy source 的 current production/test
引用均为 0。K3 为 `RESOLVED`；K4 为 `SOURCE_BOUNDARY_RESOLVED`，其最终交付包
处置为 `PACKAGE_BOUNDARY_DEFERRED_TO_R5`。R2 duplicate / legacy convergence 至此
关闭，后续不再为 dead helper 或 mixed production module 内的少量未使用 symbol
开启 R2 cleanup。

### R3

完整 E2E 后优先做 Competition behavior convergence：

- Worker 默认 1、按需最多 2 已完成；新 Mission 单 lane 不调用 decomposition
  Planner，历史多 task plan 仍可恢复；
- Verifier final-only 默认路径已完成：新普通 Task 不调用，历史
  `VERIFIER_PENDING` 可恢复，Mission 终局调用保留；高风险时的显式按需策略未新增；
- gate-first happy path 已完成离线实现：证据充分的首次普通 Task 直接运行
  deterministic Gate；证据不足、Gate FAIL、alert/retry/恢复保留 Auditor → Planner；
- 自动 master/main merge 与 origin push 已从 competition Panel runtime 删除；
  `MISSION_DONE` 只保留 verified integration，不触发用户仓库写回；
- 当前 `ClosedLoop` 仍有 bounded L0 direct worker nudge；R3 决定保留该
  fast path，还是将自动 Worker 指令统一路由 Planner；
- fingerprint 去 source 与 thread revision 支持多轮新证据继续低优先级，
  不阻塞比赛行为收敛。

### R4

收敛产品化边界：

- 项目选择已完成：Panel 读取 AO 官方 registry，新建 Mission 显式选择并在启动前
  重验 ID/path；Project 注册仍由 AO 负责；
- 生效配置；
- 人工 override；
- 审批白名单；
- 若未来需要主分支交付，单独设计用户显式 SCM 操作；不恢复 Mission DONE
  隐式 push/merge。

### R5

完成：

- CI；
- 全新 clone 安装；
- AO 官方依赖说明；
- 不携带 AO 用户数据；
- 通用项目与 Demo 模式；
- 最终比赛彩排和干净源码包。

R1、R2 主链以及 Verifier final-only、gate-first、event freshness、默认单 Worker、
自动 SCM 副作用移除与 R4 Project selector 均已完成；核心 single-worker 标准 smoke
已通过。R2 Closure Audit 已 PASS，duplicate / legacy convergence 已关闭，当前 v2
production authority 单一。历史来源继续保留在 Git repo，但不应进入最终 competition
release artifact；R5-1 Clean Release Boundary Audit 已确定 clean artifact、bootstrap
与 clean-machine first-run 边界。

R5-1 Clean Release Boundary Audit 已 PASS，并确定最终打包主策略为
`ALLOWLIST_RELEASE`。R5-2 只实现 CPython 3.12、本地 `.venv`、精确 Python
dependencies 与 Panel first-run launcher。R5-3 增加 Panel/CLI 共用的 Mission
preflight，在创建 runtime/StateStore/Worker 前检查 CPython、Git worktree/identity、
AO daemon/Project、Codex ChatGPT 登录和生产模型配置；该检查不调用模型或检查目标
项目 Gate dependencies。`交付/release-manifest.txt` 是唯一 package allowlist，
`交付/build-release.ps1` 从 clean HEAD tracked tree 构建 repo 外 staging/zip、校验
文件集合、文档链接、generated/history hygiene 与高置信 secret，并生成
`SHA256SUMS.txt`。两个 sample 已改用 `REPLACE_WITH_AO_PROJECT_ID`，不恢复 demo
fallback。下一步为 R5-4 Clean Release Rehearsal；本批未运行 AO Worker、Codex live、
完整 Mission 或 GUI。

R5-4 Clean Release Rehearsal 已 PASS。以 main
`f9905aa37bb5ffb8f5480710682e3fd760df75fc` 构建的
`closed-loop-v2-f9905aa37bb5.zip` SHA-256 为
`d499627523b43eed8af2a0e308425dd3fb59352acb52b0fad0d2a3d0ad379edf`。
彩排只使用 ZIP 在第二个全新 repo 外目录中的解压内容：pre-bootstrap hygiene 与
historical/generated 禁入项均为 0；95 条 `SHA256SUMS.txt` 独立重算 missing/mismatch/
extra 均为 0；3 个本地 Markdown 链接 missing 为 0。bootstrap 首次创建 CPython
3.12.7 venv，第二次复用且未重建，PyYAML 6.0.3、pytest 9.1.1；artifact 全量测试为
`423 passed in 73.33s`，compileall、deterministic single-worker dry-run 与 Panel
offline import 均通过，dry-run/import 前后没有 runtime。原始 ZIP 哈希保持不变；
未调用真实 AO、Codex login/model、Worker、完整 Mission 或 GUI。下一步为 R5-5
Final Live Rehearsal。

R5-5 初次启动 Worker 时在 AO 创建 Session/Codex turn 前失败，完整 root cause 为
`DEFAULT_BRANCH_UNRESOLVED`，不是网络故障。为 Project 显式设置
`defaultBranch=main` 但继续使用无 remote 的 local-only repository 后，AO 0.12.9
仍以 `WORKSPACE_CREATE_FAILED` 拒绝创建 workspace，因为实际需要
`refs/remotes/origin/main`。这否定了“显式本地分支即可支持 local-only Project”的
假设。随后使用完全本地的 bare `origin`、可解析的 `origin/main` 与指向它的
`origin/HEAD` 进行 raw AO spawn，Codex Worker turn 和精确回复均 PASS，全程不依赖
GitHub。PR #27 已将 shared preflight 收窄为这一已验证的 remote-backed contract，
并持久化经过脱敏、有界的 spawn failure root cause；R5-5 尚未通过。

R5-4.5 CLAO Product Layout 保留开发仓库中的 `交付/`、治理文档和历史来源，通过
`交付/release-manifest.txt` 的 source-to-destination mapping 只把当前产品映射到 ZIP
唯一顶层目录 `clao/`。产品名称固定为 CLAO v0.2，开发审计文档不进入 release；
下一步为 Final R5-5 Live Rehearsal。

首次从 standalone CLAO ZIP 运行 Final CLI 时，AO Worker、Task Gate、integration 与
Final Gate 均 PASS；Mission Verifier 在 transport startup 阶段因 CLAO artifact 根目录
不是 Git repository 被 Codex CLI 拒绝。Planner/Auditor/Verifier 仍保持现有 cwd 语义，
共享 `run_codex_json()` 固定加入 `--skip-git-repo-check`，不要求 standalone 产品目录
携带 `.git`。repo 外 non-Git cwd 的真实 structured Codex smoke 已返回
`R5_CODEX_NONGIT_OK`；该修复随后经审计合并，并进入 Final CLI 重跑。

R5-5 Final Live Acceptance 已 PASS。最终 live-tested product source commit 为
`6bbc499b9603bba55542989a595ae888e6f7c4f3`；测试 ZIP 为
`clao-v0.2-6bbc499b9603.zip`，SHA-256 为
`af4277b9db3277eb75fd57bde386d031f787ff972a374426ea9d3a12d9a008c8`。
artifact 使用自身 bootstrap 环境完成 `438 passed` 与 compileall；独立
`SHA256SUMS.txt` 校验 92/92 PASS。

CLI Mission `MISSION-R5-FINAL-CLI-20260905-101005` 到达 `MISSION_DONE`：只创建
1 个 AO Codex Worker，model=`gpt-5.6-sol`，Task Gate、Final Gate 与 Mission
Verifier 均 PASS；Task Verifier、decomposition Planner、Completion Auditor、
Completion Planner 调用均为 0，`LOOP_ERROR` 与 trusted-directory error 均为 0。

GUI Mission `MISSION-PANEL-20260905-103636` 已由用户完成人工 GUI 确认并到达
`MISSION_DONE`。Project selector、Timeline、Task Gate evidence、Final Gate evidence
与 Mission Verifier verdict 均 PASS，Panel errors 为 0；GUI Worker
`r5-final-20260905-100602-134-2` 已终止。Worker 期间一次可恢复 reconnect alert
没有触发 Auditor/Planner fallback，不影响最终 PASS。

一次性目标仓库的 main 与 origin/main 均保持 baseline
`8959433f5bb6558a70f4ff783fe617525fc4b6d4`，没有 automatic main/master
writeback 或 automatic push。验收后 Panel 已停止，临时 AO Project 已通过官方命令
移除，一次性 Git repo、bare origin、解压副本与 builder 输出已完成安全清理。
R5 最终状态为 `R5 COMPLETE`；下一步只执行 Final Release Closeout Build。

## 十二、停止条件

出现以下任一情况立即停止当前任务并报告：

- 工作区存在无法解释的预先改动；
- 当前分支或远端历史与任务假设不一致；
- 需要修改任务允许范围之外的文件；
- 测试依赖要求修改产品依赖文件；
- 发现真实凭据、AO 用户数据或隐私内容；
- 现有文档与代码冲突且无法由只读检查判断；
- push 或 PR 创建失败且常规重试仍无法解决。
