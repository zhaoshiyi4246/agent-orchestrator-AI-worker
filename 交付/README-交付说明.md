# 闭环多智能体系统 v0.2 — 交付说明

本目录用于组内讨论、验证和后续收敛。`closed-loop-v2/` 是当前 v0.2 主产品
候选；`clao-src/` 与 `ao-supervision-sidecar/` 是历史来源和参考实现，
不是并行的正式运行入口。

当前权威架构是仓库根目录的 `docs/PROJECT.md`；本目录的
`ARCHITECTURE-v0.2.md` 与其保持一致。

## 当前产品边界

AO 负责 Project、Session、Conversation、Agent Runtime、worktree 和 PR/SCM。
本项目在 AO 之上提供唯一的 `MissionController` 控制平面、唯一的
`StateStore` 运行状态源、Observer、Auditor、Planner、Verifier、Integration
Gate、Worker 编排和 UI 时间线。

```text
Panel / run_mission
  → MissionController
    → Planner / Auditor / Verifier（headless Codex CLI）
    → Observer / Gate（确定性程序）
    → ActionExecutor / AOAdapter → AO Codex Worker
    ↔ StateStore
  → StoreBusProjector → JSONL / Markdown / UI Timeline
```

`LoopBus` 是 Store 后置事件投影和审计展示，不是控制总线，也不是唯一 AO
传输层。用户指令经 `Panel → DirectiveChannel → MissionController` 消费；
发给 Worker 的真实指令再由 `ActionExecutor → AO` 投递。

## 当前角色契约

| 角色或程序 | 当前形态 |
|---|---|
| Planner | 项目级唯一；headless Codex CLI；默认 `gpt-5.6-sol`；不直接编辑代码 |
| Auditor | 只读语义审计；headless Codex CLI；默认 `gpt-5.6-sol`；只向 Planner 提交结果 |
| Verifier | 独立只读复核；headless Codex CLI；默认 `gpt-5.6-sol`；新 Mission 正常路径只在 Mission 终局调用，历史 `VERIFIER_PENDING` Task 恢复仍可调用 |
| Worker | AO Chat-mode Codex Worker；harness=`codex`；model=`gpt-5.6-sol` |
| Observer | 确定性程序；无模型 |
| Integration Gate | 确定性程序；无模型 |

Auditor、Verifier 和 Observer 都不直接向 Worker 下发自动执行指令。当前系统
仍允许多个子任务；默认单 Worker、按需第二 Worker 仍待后续收敛。VerifierProvider
仍是正式角色；高风险子任务的显式按需策略尚未实现。

当前正常路径为：

```text
Worker
→ Completion Auditor
→ Planner
→ deterministic Task Gate
→ DONE

materialization
→ integration
→ Final Gate
→ Mission Verifier
→ MISSION_DONE / HUMAN
```

新 Task Gate PASS 不调用 Task Verifier、不写 task-level verification row；历史
runtime 若已处于 `VERIFIER_PENDING`，仍按旧 task verifier 路径恢复。Mission
Verifier 是新 Mission 默认唯一的正常路径 Verifier 调用。

## 目录结构

```text
ARCHITECTURE-v0.2.md          v0.2 当前架构说明
PV-独立验证任务.md            历史独立产品验证任务书
AO_UPGRADE_CHECKLIST.md       AO 版本升级验收流程
ao-openapi-diff.py            OpenAPI 契约对比工具

closed-loop-v2/               当前主产品候选
  src/loopcore/               Mission、Store、AO 边界、Observer、Gate、Provider
  panel/                      server.py + index.html，本地 Web 面板（7100）
  prompts/                    Planner/Auditor/Verifier 角色契约
  config/default.yaml         当前运行配置
  schemas/                    JSON Schema
  tasks/mission-quick.json    当前 Codex dry-run 示例
  run_mission.py              CLI 与运行时组装入口
  启动面板.bat                 面板启动入口
  tests/                      v0.2 自动化测试

clao-src/                     历史来源与参考实现
ao-supervision-sidecar/       历史来源与参考实现
closed-loop-demo/             演示目标仓库
closed-loop-demo-origin.git/  演示 bare origin
```

R2 完成调用关系证明前，不删除历史来源目录或旧兼容模块。

## AO 运行时与用户交付边界

R2-0 已从当前生产主路径移除开发者绝对 AO 路径。AO Desktop 是外部依赖，不随
本源码目录打包、安装或自动启动：

- executable：`CLAO_AO_BIN` → PATH 中的 `ao`；
- runfile：`CLAO_AO_RUN_FILE` → `~/.ao/running.json`；
- 正常 Mission 启动/恢复必须能够解析 AO executable，否则 fail fast；
- Panel 只读查看已有 Mission 存档不要求 AO executable，也不连接 AO、调用
  Codex 或创建 Worker。

上述结论只表示“运行时路径可移植”，不表示“任意用户零配置安装”。clean clone
bootstrap/安装脚本、AO 首次配置 UX、Project 注册与选择仍未完成；当前交付不能
宣称为通用安装包或解压即用产品。

## 当前已实现与后续事项

当前已实现：

- Panel 发起 Mission；
- Planner 自动分解；
- Panel/CLI 的 AO Codex Worker 执行；
- Observer 确定性观察；
- Auditor → Planner 闭环；
- deterministic Task Gate、Mission Final Gate 和 Mission Verifier；
- StateStore 恢复、stop/resume；
- UI 时间线与派生的 Markdown/JSONL。

仍待后续：

- Verifier final-only 已完成，合并当前 PR 后待一次同题真实性能 E2E；
- 下一项进行 Completion Auditor / Planner happy-path convergence；
- 默认 1 个 Worker、按需最多 2 个，以及隐藏或显式标记
  `auto_ff_master` 为实验性高风险功能，仍待后续；
- 比赛行为收敛后再做重复模块和旧入口清理；
- 最后完成 clean delivery、installer/bootstrap、AO first-run 和 CI 收尾；
- fingerprint/source 与 thread revision 继续保持低优先级。

Project 注册/选择与其他首次配置 UX 归比赛 UX/R4，`auto_ff_master` 的 legacy
data root 和权限边界归 Competition convergence/R4，clean clone 安装归最终
clean-delivery 阶段。

## 本地验证

已验证基线使用 Python 3.12、本地 `.venv`、独立安装并运行的 AO Desktop，
以及已通过 ChatGPT 登录的 Codex CLI。

真实 Mission 启动前必须先安装并运行 AO Desktop。若 PATH 已有 `ao`，无需设置
executable；否则在当前进程设置 `CLAO_AO_BIN`。非标准 daemon runfile 才需要
设置 `CLAO_AO_RUN_FILE`，默认读取 `~/.ao/running.json`。

```powershell
cd closed-loop-v2
$venvScripts = (Resolve-Path ".\.venv\Scripts").Path
$env:PATH = "$venvScripts;$env:PATH"
$env:PYTHONPATH = (Resolve-Path ".\src").Path

.\.venv\Scripts\python.exe -m pytest .\tests -q
.\.venv\Scripts\python.exe -m compileall -q .\src .\panel .\run_mission.py
.\.venv\Scripts\python.exe .\run_mission.py .\tasks\mission-quick.json --dry-run
```

`--dry-run` 是 Planner 分解预检：它会调用真实 Codex Planner，但不连接 AO、
不创建 Worker、不创建 StateStore 或 runtime。真实运行还需要 AO daemon 在线，
且目标 Project 已在 AO 注册。

测试数量以 CI 或当前真实命令输出为准，不在交付说明中冻结。

## 不作为源码交付的内容

- AO Desktop 安装目录与 AO 用户数据；
- 真实 Session、Conversation、凭据、Cookie 和日志；
- `.venv/`、`__pycache__/`、`.pytest_cache/`；
- `closed-loop-v2/runtime/` 及面板生成的任务存档；
- 历史 worktree、运行数据库和本机缓存。
