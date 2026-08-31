# v0.2 修正计划

- 当前阶段：R1 — Provider 迁移与架构事实统一
- 当前任务：实现并验证 Codex CLI Provider，先迁移 Planner 并恢复 dry-run
- 当前状态：进行中
- 下一步：在独立代码任务中实现共享 Codex CLI 调用边界，先迁移 Planner，
  保持现有 schema/validator 与 `MissionController` 控制边界

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
| R1 | Codex Provider 迁移、架构事实、文档、代码注释与前端拓扑统一 | 进行中 |
| R2 | 重复模块、旧入口和参考代码收敛 | 未开始 |
| R3 | Worker 数量、Verifier、issue/thread 与控制语义收敛 | 未开始 |
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
| 初始化 PR | `#1`，状态 OPEN，目标分支 `main`，未合并 |

R0 关闭结论：治理文件、主路径与重复模块盘点已建立；完整 pytest、compileall、
Codex ChatGPT 登录与 GPT-5.6 Sol headless probe 均已通过。旧 dry-run 失败已准确
分类为待迁移实现，不再作为 R0 阻塞，R0 因此完成。

环境或依赖阻塞时，记录原始错误并区分：

- 代码失败；
- 本地环境缺失；
- AO/模型等外部依赖未启动。

不得为了通过 R0 修改产品代码。

## 五、已知问题清单

| 编号 | 问题 | 计划阶段 | 状态 |
|---|---|---|---|
| K1 | 旧架构文档与代码主路径不一致 | R1 | 已确认：角色运行形态、Bus 职责和入口描述均与代码不同 |
| K2 | Loop Bus 文档职责与 Bus Projector 实际职责不一致 | R1 | 已确认：当前 Bus 是 Store 后置审计投影，不是控制或 AO 指令路径 |
| K3 | 多套 AO Client、Observer、Gate、协议与 CLI | R2 | 已确认：主路径与兼容/历史模块同时存在 |
| K4 | `clao-src`、sidecar 与主产品同时交付，边界不清 | R2 | 已确认：三者同时交付；主路径无跨目录 import，来源目录当前仅作参考 |
| K5 | 默认强制拆成至少两个 Worker | R3 | 已确认：面板和示例默认 `max_subtasks=2`，Planner 提示要求 `2..max` |
| K6 | Verifier 使用过重且旧文档允许绕过 Planner | R3 | 已确认：当前每个子任务和 Mission 终局都调用 Verifier；实际结果回 Controller/Planner 路径 |
| K7 | issue fingerprint 包含 source | R3 | 已确认：`issue_fingerprint()` 返回值显式包含 `source` |
| K8 | thread 缺少 revision 裁决语义 | R3 | 已确认：同一 issue 只允许一次 verdict，没有 revision 字段或重裁决路径 |
| K9 | 多套状态与投影没有明确主从 | R1/R2 | 已否定：代码主从已明确为 StateStore/AO Worker 事实与后置投影；文档表达仍需 R1 统一 |
| K10 | 配置项重复、未接线或 UI/后端语义不同 | R4 | 已确认：`roles.*`、`roles.max_parallel_workers`、`ao.base_url` 等未被当前组装路径完整消费 |
| K11 | 面板偏向 bundled demo，缺少真实 Project 选择 | R4 | 已确认：项目缺省/回退均为 `closed-loop-demo`，没有 AO Project 列表选择路径 |
| K12 | 自动审批和自动 push 边界过宽 | R4 | 已确认：自动审批已接线；`auto_ff_master` 默认关闭但可由面板 API 开启并 push |
| K13 | 测试数量与冻结状态文档不一致 | R0/R1 | 已确认：文档声称 247/272，本次实际收集 252 项 |
| K15 | 当前 Planner/Auditor/Verifier 与 `llm_env` 绑定 Claude CLI、`ANTHROPIC_MODEL` 和 `GLM-5.2` | R1 | 已确认：目标改为 Codex CLI + GPT-5.6 Sol |
| K16 | 当前 Worker 默认 `worker_harness=claude-code`、`worker.model=GLM-5.2` | R1 | 已确认：目标改为 AO Codex harness + GPT-5.6 Sol；具体 AO harness/model 参数必须通过本机 live probe 确认 |
| K17 | 旧 README、`ARCHITECTURE-v0.2.md` 和 `default.yaml` 明确写有“不使用 Codex”或 Claude/GLM 依赖 | R1 | 已确认：后续独立任务统一清理，不在 R0 修改 |

## 六、阶段边界

### R1

按独立小任务迁移 Provider 并统一事实与展示，不做一次性大重构或大规模删除。
第一任务是“实现并验证 Codex CLI Provider，先迁移 Planner 并恢复 dry-run”。其后
再分别迁移 Auditor/Verifier、依据本机 live probe 迁移 AO Worker，并清理 K17 文档
和配置表述。目标：

- `MissionController` 唯一控制平面；
- `StateStore` 唯一 CL-AO 状态源；
- Bus 改为 Event Projection；
- 前端拓扑区分逻辑角色与真实物理调用；
- README、架构文档、代码注释一致。
- Planner/Auditor/Verifier 共享一个 ephemeral、read-only、结构化输出的 Codex CLI 调用边界；
- Worker 使用经本机 live probe 验证的 AO Codex harness/model 参数。

### R2

先生成调用关系，再每次只收敛一组重复实现。删除前必须有测试和入口证据。

### R3

收敛控制语义：

- Worker 默认 1，最多 2；
- Verifier 终局/高风险可选；
- 自动指令统一由 Planner 发出；
- fingerprint 去 source；
- thread revision 支持多轮新证据。

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

## 七、停止条件

出现以下任一情况立即停止当前任务并报告：

- 工作区存在无法解释的预先改动；
- 当前分支或远端历史与任务假设不一致；
- 需要修改任务允许范围之外的文件；
- 测试依赖要求修改产品依赖文件；
- 发现真实凭据、AO 用户数据或隐私内容；
- 现有文档与代码冲突且无法由只读检查判断；
- push 或 PR 创建失败且常规重试仍无法解决。
