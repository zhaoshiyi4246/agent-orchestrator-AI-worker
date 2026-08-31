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
| Verifier | 独立只读复核；headless Codex CLI；默认 `gpt-5.6-sol`；当前在子任务 Gate 后和 Mission 终局调用 |
| Worker | AO Chat-mode Codex Worker；harness=`codex`；model=`gpt-5.6-sol` |
| Observer | 确定性程序；无模型 |
| Integration Gate | 确定性程序；无模型 |

Auditor、Verifier 和 Observer 都不直接向 Worker 下发自动执行指令。当前系统
仍允许多个子任务；默认单 Worker、按需第二 Worker，以及终局/高风险才调用
Verifier，是 R3 的后续目标。

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

## 当前已实现与后续事项

当前已实现：

- Panel 发起 Mission；
- Planner 自动分解；
- Panel/CLI 的 AO Codex Worker 执行；
- Observer 确定性观察；
- Auditor → Planner 闭环；
- Integration Gate 和当前 Verifier；
- StateStore 恢复、stop/resume；
- UI 时间线与派生的 Markdown/JSONL。

仍待后续：

- R2 的重复模块和旧入口清理；
- R3 的默认单 Worker、按需第二 Worker 和 Verifier 调用策略；
- R4 的任意 AO Project 选择、配置接线和自动审批权限；
- R5 的 AO 路径/安装可移植性、CI 和干净交付。

AO Desktop 不随源码目录作为一个安装包交付。当前环境仍含本机 AO 路径假设，
不能宣称任意电脑解压即可运行。

## 本地验证

已验证基线使用 Python 3.12、本地 `.venv`、独立安装并运行的 AO Desktop，
以及已通过 ChatGPT 登录的 Codex CLI。

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

当前 `main` 基线在 R1-3 验证时为 **295 passed**；以后以 CI/当前测试输出为准。

## 不作为源码交付的内容

- AO Desktop 安装目录与 AO 用户数据；
- 真实 Session、Conversation、凭据、Cookie 和日志；
- `.venv/`、`__pycache__/`、`.pytest_cache/`；
- `closed-loop-v2/runtime/` 及面板生成的任务存档；
- 历史 worktree、运行数据库和本机缓存。
