[README.md](https://github.com/user-attachments/files/31627080/README.md)
# 闭环多智能体系统 v0.2

> 基于 Agent Orchestrator（AO）的多智能体闭环开发系统 ——
> **智能体自报完成 ≠ 项目真正完成。** 本系统在 AO 的 Agent 运行、会话、
> worktree 与 PR 能力之上，增加一层独立的闭环控制层，让
> Planner / Auditor / Observer / Verifier / Worker 五种角色以
> 有界自治的方式协作完成真实编码任务。

---

## 1. 产品组成

| 角色 | 数量 | 本质 | 职责 |
|---|---|---|---|
| Planner | 1（唯一） | LLM agent（Claude） | 接纳用户任务、拆解派发；根据审计/验证证据裁决 PASS / LOCAL_FIX / REPLAN / HUMAN；撰写 memory.md 与 project.md；最终向用户汇报 |
| Auditor | 1（只读） | LLM agent（Claude） | 依据任务目标、验收条件与证据做语义审计；发现 Worker 卡住时介入纠错；大问题提交 Planner 裁决 |
| Observer | 1 | **确定性程序**（非 agent） | 固定间隔轮询 AO；识别完成里程碑、重复失败、停滞；错误指纹首次出现即预警；预算消耗 80% 预警 |
| Verifier / Integration Gate | 1 | **确定性程序** + LLM 复核 | 里程碑触发验证；代码合并后运行项目级测试，失败证据自动回传 Auditor / Planner / Worker |
| Worker | ≥2（按需孵化） | LLM agent（GLM-5.2） | 接收 Planner 派发的任务与 LOCAL_FIX 局部修复指令，在 AO worktree 中真实编码 |

**设计原则**：确定性判断由普通程序完成，语义判断才调用 LLM；不为"多智能体"堆叠角色；有界循环 + 超时 + 人工兜底。

### 通道矩阵（两两关系精确设计）

| 通道 | 方向 | 说明 |
|---|---|---|
| Planner ↔ Worker | 双向 | 派发任务 / 汇报进展、上报困难 |
| Planner ↔ Auditor | 双向 | 审计请求 / 审计结论 |
| Planner ↔ Verifier | 双向 | PV 任务派发 / 验证结论回传 |
| Planner ↔ Observer | 双向 | 调整观察焦点 / 风险信号 |
| Auditor ↔ Worker | 双向 | 纠错介入 / 主动上报 |
| Auditor ↔ Observer | 双向 | 定向观察请求 / 触发证据 |
| Worker ↔ Observer | 双向 | 状态备注 / 停滞提醒 |
| Worker ↔ Verifier | 双向 | 验证请求 / 结果回传 |
| **Auditor → Verifier** | **单向** | 验证结论出口唯一收敛到 Planner，防止监督方绕过裁决层 |
| **Observer → Verifier** | **单向** | 同上 |

用户可从面板指令栏向**任意一个** agent 直接下达指令：发给 Planner 的指令仅 Planner 可见；发给其他任何 agent 的指令，该 agent 与 Planner 均可见（前后端均已实现）。

---

## 2. 系统要求

| 依赖 | 说明 |
|---|---|
| Windows 10/11 x64 | 已在此平台完整验证 |
| Python 3.10+（加入 PATH） | 运行闭环控制层；`安装.bat` 会自动创建虚拟环境 |
| Node.js | Claude CLI 的运行时 |
| Claude CLI | 位于 `%APPDATA%\npm\claude.cmd`，程序自动查找 |
| Git Bash | Claude CLI 在 Windows 上的硬性依赖 |
| 网络连接 | 调用模型 API（Planner/Auditor/Verifier 用 Claude，Worker 用 GLM-5.2，不使用 Codex） |

## 3. 包内容

```text
最终交付成果/
├─ README.md                ← 本文件
├─ 安装.bat                 ← 一键安装闭环控制层依赖并自检
├─ 启动AO.bat               ← 一键启动 AO（自动使用本包预配置数据）
├─ requirements.txt
├─ ao-app/                  ← Agent Orchestrator 桌面应用（底层运行平台）
├─ ao-data/                 ← AO 预配置数据（网关模型、demo 项目注册）
├─ closed-loop-v2/          ← 闭环控制层（本产品本体）
│   ├─ 启动面板.bat         ← 一键启动可视化控制台
│   ├─ panel/               ← Web 控制台（前端 + 服务）
│   ├─ src/loopcore/        ← 闭环核心（Bus/Observer/Gate/协议……）
│   ├─ config/default.yaml  ← 全部可调参数（角色模型、时间阈值……）
│   ├─ prompts/             ← 角色契约提示词
│   ├─ tests/               ← 272 项离线测试
│   └─ docs/ARCHITECTURE-v0.2.md  ← 权威设计基线
└─ demo/
    ├─ closed-loop-demo/          ← 示例项目仓库
    └─ closed-loop-demo-origin.git ← 示例远程仓库（供 AO worktree/PR 流程）
```

## 4. 安装与启动（三步）

1. **安装**：双击 `安装.bat`（首次约 1–3 分钟：建虚拟环境 → 装依赖 → 跑 272 项自检）。
2. **启动 AO**：双击 `启动AO.bat`，等待 AO 桌面窗口出现（守护进程监听 `127.0.0.1:3001`）。
3. **启动控制台**：双击 `closed-loop-v2\启动面板.bat`，浏览器自动打开 `http://127.0.0.1:7100`。

> 日常使用时安装只需一次；之后每次使用执行第 2、3 步即可。

## 5. 快速开始：跑一个真实任务

1. 在面板顶部表单中填写：
   - **项目**：`closed-loop-demo`（AO 中已预注册）
   - **任务目标**：例如 `为 math2.py 增加 clamp01(x) 函数，将输入钳制到 [0,1]`
   - **验收条件**：每行一条，例如 `clamp01(1.5) == 1`、`clamp01(-0.2) == 0`
   - **Gate 命令**：默认 `python -m pytest -q`（项目级测试，合并后强制运行）
   - **最大子任务数**：默认 2（对应 2 个 Worker 并行上限）
2. 点击开始，观察：
   - **拓扑图**：Planner / Auditor / Observer / Verifier / Worker 节点与通道实时连线（Worker 按实际孵化数量动态绘制）
   - **事件流**：Observer 触发、审计结论、Planner 裁决、Gate 结果逐条滚动
   - **指令栏**（底部固定）：选择任一 agent 直接下达或修改指令
   - **memory.md / project.md**：Planner 实时撰写的项目记忆与重大事项进展，面板可直接查看
3. 任务结束时由 **Planner 汇总结论并报告给用户**；失败/超限自动转人工兜底，不会死循环。

### 时间参数（用户可精确调控，输入多久就是多久）

面板或 `config/default.yaml` 中可调：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `observer.interval_seconds` | **10 s** | Observer 轮询间隔（推荐 10 s） |
| `auditor.audit_interval_seconds` | **300 s（5 分钟）** | 例行审计节奏（推荐 5 分钟；有触发时立即审计） |
| `observer.stall_threshold_seconds` | 300 s | 停滞判定阈值 |
| `bus.overall_timeout_seconds` | 600 s | 单任务总体超时，超限转人工 |

## 6. 故障排查

| 现象 | 处理 |
|---|---|
| 面板提示连不上 AO | 确认已通过 `启动AO.bat` 打开 AO 桌面窗口，且 `127.0.0.1:3001` 可访问 |
| Worker 孵化失败 / claude 找不到 | 确认 Claude CLI 在 `%APPDATA%\npm\claude.cmd`，且已安装 Git Bash |
| Gate 超时 | 调大 `gate.timeout_seconds`（默认 300 s） |
| 7100 端口被占 | 设环境变量 `PANEL_PORT` 换端口后再启动面板 |
| 想把本包移动到其他目录 | 移动后需：① 在 demo 仓库内执行 `git remote set-url origin <新路径>\demo\closed-loop-demo-origin.git`；② 在 AO 中重新注册 demo 项目路径。闭环控制层自身路径无关，无需改动 |

## 7. 质量基线（v0.2 冻结）

- **272 项离线自动化测试**全部通过（MockTransport，不访问真实网络）
- **独立 PV 验证 S1–S9 全部通过**（含 Gate Pass、可控失败闭环、停止指令真停止等场景）
- 冻结基线：git `098651b` 及后续清理提交（`c58a664`）
- 架构权威文档：`closed-loop-v2/docs/ARCHITECTURE-v0.2.md`

## 8. 已知边界

- 面向技术用户的 v0.2，非零配置商业产品：首次需按第 4 节完成三步安装启动
- Planner / Auditor / Worker 的创建与角色注入在本版本为半自动（面板一键下发任务后系统自动孵化与管理）
- AO 官方升级后：本系统仅依赖 AO 公开 REST 与 `ao spawn` CLI 契约；若 AO 数据格式变化，重新注册项目即可恢复，控制层代码无需改动

---

*开发方交付 · 2026-08-31 · 版本 v0.2*
