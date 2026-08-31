# Codex 项目规则

本文件位于仓库根目录，适用于整个仓库。更深层目录若以后新增 `AGENTS.md`，只可补充局部规则，不得破坏本文件中的项目级不变量。

## 一、开始任何任务前

依次完成：

1. 阅读 `docs/PROJECT.md`；
2. 阅读 `PLANS.md`；
3. 阅读与当前任务直接相关的源码和测试；
4. 执行 `git status --short --branch`；
5. 确认当前分支、允许修改范围、验收条件和停止条件。

不要仅根据文件名判断模块是否在用。删除、迁移或合并模块前，必须检查入口、import、调用关系、测试和文档引用。

## 二、核心原则

- 遵循“如无必要，勿增实体”。
- 每次只完成当前任务要求的最小闭环，不顺带重构无关代码。
- 确定性判断由普通程序完成；语义判断才调用 LLM。
- 不为“多智能体”数量而拆分任务或新增角色。
- 不把未经运行验证的能力写成已完成事实。
- 遇到协议不明、状态矛盾、范围越界或高风险写操作时，停止并明确报告，不猜测。

## 三、仓库与产品边界

- `交付/closed-loop-v2/` 是当前 v0.2 主产品候选路径。
- `交付/clao-src/` 与 `交付/ao-supervision-sidecar/` 暂视为历史来源和参考实现。
- 在 R2 完成调用关系证明前，不删除上述参考目录，也不得把它们当作第二套正式产品入口。
- `交付/closed-loop-demo/` 与 `交付/closed-loop-demo-origin.git/` 是演示夹具，不是产品运行状态源。
- 不重新实现 AO 已有的 Project、Session、Agent Runtime、worktree、PR、SCM 和生命周期能力。

## 四、目标架构不变量

- `MissionController` 是目标唯一控制平面。
- `StateStore` 是目标唯一 CL-AO 运行状态源。
- AO 的公开 Session、Conversation、activity 与 workspace 快照是 Agent 运行事实源。
- Loop Bus 的目标定位是事件投影、审计时间线和 UI 展示，不是第二套控制平面，也不是唯一 AO 传输层。
- Markdown、JSONL、拓扑图和前端缓存均为派生视图，不参与恢复、裁决或控制。
- Planner 项目级唯一。
- Worker 默认 1 个；只有任务确实可以独立拆分时才启用第 2 个，当前目标上限为 2 个。
- Observer 与 Integration Gate 必须保持确定性程序，不得升级为 Agent。
- Auditor 只做语义审计并向 Planner 提交结论，不直接向 Worker 下发自动执行指令。
- Verifier 仅用于最终合并或高风险独立复核，只向 Planner 提交证据，不直接控制 Worker。
- 只有 Planner 可以向 Worker 下发自动执行指令。
- 用户对非 Planner 角色的直接指令必须被视为显式人工 override，并可追踪地暂停或替代当前自动流程，不能与自动指令静默并行。
- 当前目标 LLM Provider 是 Codex CLI：Planner、Auditor、Verifier 使用 headless Codex Provider，Worker 使用 AO 中的 Codex harness。
- 目标默认模型为 `gpt-5.6-sol`，但模型选择必须保持可配置，不得成为永久架构不变量。
- Observer 与 Integration Gate 不使用模型。
- 默认路径复用 Codex CLI / AO Codex 的 ChatGPT 登录，不以 OpenAI API Key 接入作为默认路径。
- 不再新增 Claude、GLM、Kimi 等第二套默认 Provider。

## 五、禁止无必要新增

除非当前任务证明其不可替代，否则不得新增：

- 新 Agent 或第二个 Planner；
- 第二个数据库或第二套状态机；
- 后台常驻服务、消息队列、MCP Server 或新 Agent 框架；
- 新 Web 框架、事件总线或 repository/service/manager 抽象层；
- 目标项目根目录中的运行时记忆文件；
- 自研 AO worktree、PR 或 Session 生命周期替代层；
- 默认自动 push、自动 merge 或破坏性 Git 操作。

## 六、高风险边界

- 默认不得自动执行 `git push`、`git reset`、`git clean`、`git restore` 或破坏性 `git checkout`。
- 自动审批不得允许 shell 拼接、命令注入、权限提升、密钥访问或目标项目范围外写入。
- 自动 push、自动合并和破坏性审批即使已有实现，也必须保持默认关闭，除非专门任务重新审计并验收。
- 不提交真实 AO 数据、用户会话、模型凭据、Cookie、日志、运行数据库、`.venv`、缓存、绝对本机路径或历史 worktree。

## 七、代码修改纪律

- 优先复用当前主路径，不复制第二套实现。
- 修改协议、状态机或消息方向时，必须同时更新相关测试和 `docs/PROJECT.md`。
- 删除旧模块前必须给出：
  1. 入口与 import 搜索结果；
  2. 运行路径证明；
  3. 测试覆盖；
  4. 回滚影响。
- 配置项必须有真实消费者；未接线配置应删除或明确标记为保留，不得伪装成已生效。
- Provider 迁移必须在独立代码任务中完成；R0 只记录目标基线，不修改运行时代码。

## 八、验证纪律

- 先运行与改动直接相关的测试，再运行已验证的完整基线。
- 不虚构测试数量；以本次真实命令输出为准。
- 命令失败时保留原始错误，区分代码问题、环境问题和外部依赖问题。
- 纯文档任务至少运行：
  - `git diff --check`
  - 文档链接和路径一致性检查
- 代码任务至少运行：
  - 相关单元测试
  - 完整 v0.2 测试基线
  - `compileall` 或等价语法检查
- R0 完成后，将实际可复现的环境与命令记录到 `PLANS.md`；后续任务使用该基线，不自行发明另一套命令。

## 九、Git 与 PR

- 每个任务使用独立分支和 Pull Request。
- 不直接修改或推送 `main`。
- 不 amend 或 force-push，除非任务明确要求处理当前 PR 的 rebase，且只能使用 `--force-with-lease`。
- 最终提交前检查：
  - `git status --short`
  - `git diff --check`
  - `git diff --cached`
- PR 正文必须包含：目标、范围、验证结果、已知边界和未完成事项。
- 合并由用户在审计通过后执行，Codex 不自行合并 PR。

## 十、文档维护

- `docs/PROJECT.md`：当前权威架构、职责与边界。
- `PLANS.md`：阶段、当前任务、真实证据和下一步。
- 旧的 `交付/ARCHITECTURE-v0.2.md` 暂作为历史设计输入；修正期间若与 `docs/PROJECT.md` 冲突，以后者为准。
- `PLANS.md` 只在阶段、任务状态或验证证据发生变化时更新，不记录聊天过程、临时推理或大段终端日志。
