# csi-nanobot-sdk → csi-back 集成迁移计划

> 本文档描述将 `csi-nanobot-sdk` 整体迁入 `csi-back` 后端（最终位置：`csi-back/app/service/nanobot/`），并将所有持久化从文件系统改为 MongoDB 的实施方案。项目迁移完成后不再保持与上游 nanobot 的同步。

---

## 一、目标与边界

### 1.1 总体目标

- 把当前 `csi-nanobot-sdk` 整包移入 `csi-back/app/service/nanobot/`，不作为外部依赖包使用。
- 全部持久化（配置、会话、记忆、历史、技能状态等）改为 MongoDB（Beanie/Motor），复用 `csi-back` 已有的数据库栈。
- 在 `csi-back` 层用 nanobot 完整替换 `app/service/agent/` 下的 LangChain 实现，保留现有对外 API（`/agent/*` 路由行为不变）。
- 保留 LangChain 版已有的关键业务能力：多模型/模板/Agent 配置、HITL 审批、`write_todos`、SSE 实时状态、暂停/取消/恢复、结构化最终结果。
- **本期先跑通核心流程**：Skills DB 化、Sandbox、Tool 粒度权限、Dream 逻辑优化都留到后续迭代。

### 1.2 本期不做（后续迭代）

- Skills 独立 CRUD 与数据库化（本期仍用源码目录里的静态 md 文件）。
- Sandbox（workspace 工具先整体禁用，代码保留）。
- 按 agent 粒度的工具/技能白名单动态下发（本期由 `ToolsConfig` 硬编码）。
- 跨 agent 知识共享 / 全文检索召回。

---

## 二、当前架构分析

### 2.1 csi-nanobot-sdk 侧：持久化落点清单

> 下表是接下来**每一项都要改成 MongoDB**（或清理掉）的完整清单。


| 模块             | 源文件                                                                | 当前落盘                                                      | 作用                                      | 迁移目标                                            |
| -------------- | ------------------------------------------------------------------ | --------------------------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| 全局配置           | `nanobot/config/loader.py`                                         | `~/.nanobot/config.json`                                  | Providers / AgentDefaults / Tools / MCP | `nanobot_configs` 集合                            |
| 运行时路径派生        | `nanobot/config/paths.py`                                          | `~/.nanobot/{cron,logs,media,...}`                        | 各子目录路径                                  | 大部分删除；仅保留媒体临时目录用于上传缓存                           |
| 会话             | `nanobot/session/manager.py`                                       | `{workspace}/sessions/{key}.jsonl`                        | 会话 metadata + messages                  | `nanobot_sessions` + `nanobot_session_messages` |
| 长期记忆           | `nanobot/agent/memory.py::MemoryStore`                             | `{workspace}/memory/MEMORY.md`、`SOUL.md`、`USER.md`        | 长期事实 / 人格 / 用户画像                        | `nanobot_memory_docs`                           |
| 历史条目           | 同上                                                                 | `{workspace}/memory/history.jsonl`                        | append-only 摘要条目                        | `nanobot_history`                               |
| 游标             | 同上                                                                 | `.cursor` / `.dream_cursor`                               | 最新 cursor / Dream 已处理 cursor            | `nanobot_history_state`                         |
| 记忆版本控制         | `nanobot/utils/gitstore.py`                                        | `{workspace}/.git` (dulwich)                              | 版本/line_ages                            | **清理（见 §4.2）**                                  |
| 技能             | `nanobot/agent/skills.py`                                          | `{workspace}/skills/*/SKILL.md` + 源码内置 `nanobot/skills/`* | SKILL.md + frontmatter                  | **本期仅保留源码内置目录**；workspace skills 不启用            |
| 定时任务           | `nanobot/cron/service.py`                                          | `{cron_dir}/store.json`+`action.jsonl`+lock               | 定时 job                                  | **清理（见 §4.1）**                                  |
| 工作区工具          | `nanobot/agent/tools/{filesystem,shell,search,notebook,web,spawn}` | 直接读写 workspace 文件                                         | 文件/命令/浏览/Web                            | **代码保留，默认全关**，等后续 sandbox                       |
| MCP 连接         | `nanobot/agent/tools/mcp.py` + `ToolsConfig.mcp_servers`           | 配置项                                                       | 外部 MCP 服务                               | 保留，随 `nanobot_configs` 一起入库                     |
| 运行时 checkpoint | `AgentLoop._set_runtime_checkpoint`                                | 写入 `session.metadata`                                     | 中断恢复                                    | 随 session 入库即可                                  |


### 2.2 csi-back 侧：LangChain 现状与业务能力

关键文件：`app/service/agent/{agent.py,tools.py,motor_checkpinter.py}`、`app/models/agent/{agent,configs,checkpoint}.py`、`app/api/v1/endpoints/agent.py`。

**迁移时保留**的能力（全部通过 nanobot + hook + 业务工具等价实现）：

1. 配置 CRUD：`AgentModelConfigModel` / `AgentPromptTemplateModel` / `AgentModel`（**保留**，与 nanobot 正交）。
2. 会话业务状态：`AgentAnalysisSessionModel`（**保留**，继续作为前端可见的 `status/steps/todos/pending_approval/result` 容器）。
3. 对外路由：`/agent/configs/`*、`/agent/agents`、`/agent/start`、`/agent/status (SSE)`、`/agent/approve`（**路径与响应不变**）。
4. HITL：`modify_entity` 审批。
5. `write_todos` 任务分解。
6. SSE 事件：`status / approval_required / result / message`。
7. 暂停 / 取消 / 恢复。
8. 结构化最终结果 `ResultPayloadSchema`。

**迁移时删除**的：

1. `motor_checkpinter.py`、`CheckpointModel`、`CheckpointWriteModel`（被 nanobot 自己的 session+checkpoint 机制取代）。
2. `app/service/agent/agent.py`（整个 langchain 版 `AgentService`）。
3. `app/service/agent/tools.py`（改写为 nanobot `BaseTool`）。
4. requirements 里 `langchain / langgraph / langchain-openai / langchain-core / langgraph.checkpoint.mongodb` 全部。

---

## 三、已对齐的设计决策


| 决策点                                      | 结论                                                                                                                         |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 存储选型                                     | 所有 nanobot 数据 → **MongoDB**（Beanie）；ES 维持不变只服务实体检索                                                                         |
| 记忆隔离粒度                                   | `workspace_key = agent_id`（按 agent 隔离；不按 thread 也不全局共享）                                                                    |
| Dream 触发                                 | 默认关闭；**改为基于 token 预测触发**：`当前 prompt tokens + Dream 自身提示词 tokens ≥ context_window × 90%` 时强制执行一次 Dream                      |
| Cron                                     | **迁移前彻底清理**（模块、工具、测试、skill md 全删）                                                                                          |
| GitStore                                 | **迁移前彻底清理**（含 `annotate_line_ages`、`MemoryStore.git`、相关 command/skill/ignore 逻辑）                                           |
| workspace 工具（fs/exec/web/spawn/notebook） | 代码保留；`ToolsConfig` 默认全关；后续 sandbox 上线再放开                                                                                   |
| builtin skills                           | 保留源码目录（`nanobot/skills/`*），**cron skill 一并删除**，`SkillsLoader` 只从源码内置目录读；workspace skill 不启用                                |
| Model Provider                           | 每个 Agent 实例化时从 `AgentModelConfigModel` 读取 `base_url/api_key/model` + `AgentModel.llm_config`，映射到 nanobot 的 `AgentDefaults` |
| 目标路径                                     | `csi-back/app/service/nanobot/`，与现有 `app/service/agent/` 同级；迁入后删除旧 `agent/` 目录                                             |


### Dream 新触发策略（细化）

文件：`nanobot/agent/memory.py::Consolidator`、`Dream`、`AgentLoop`。

- `DreamConfig` 字段变更：  
  - 保留 `max_batch_size` / `max_iterations` / `model_override`。  
  - 删除 `interval_h` / `cron` / `build_schedule` / `describe_schedule`（跟 cron 一起走）。  
  - 新增 `force_trigger_ratio: float = 0.9`（可 agent 配置覆盖）。
- 在 `AgentLoop._process_message` 调用 `consolidator.maybe_consolidate_by_tokens` 之前新增一步 `dream.maybe_force_run(session)`：  
  - 估算 `current_prompt_tokens` + Dream Phase 1 提示词 tokens（提示词 tokens 预先 tokenize 一次缓存）。  
  - 若 `>= context_window_tokens × force_trigger_ratio`，同步执行一轮 Dream（仅处理到 `min(batch, unprocessed)` 条）。
- 保留 `Dream.run()` 语义，但调用入口从"定时 cron 驱动"改为"token 阈值驱动"。后续如果需要周期化，可以再在 service 层用 `asyncio.create_task` + `asyncio.sleep` 另起，跟 nanobot 内部 cron 解耦。

---

## 四、迁移前预清理（阶段 0）

> 本阶段在 csi-nanobot-sdk 内完成。完成标志：`pytest` 全绿、`nanobot_tester.py` 能跑通对话。

### 4.1 Cron 清理清单

**删除目录/文件**：

- `nanobot/cron/`（`__init__.py`、`service.py`、`types.py`）
- `nanobot/agent/tools/cron.py`
- `nanobot/skills/cron/`（整个 skill 目录）
- `nanobot/heartbeat/`（`__init__.py`、`service.py`——heartbeat 本质上依赖 cron）
- `nanobot/utils/evaluator.py`（"Post-run evaluation for background tasks (heartbeat & cron)"）
- 测试：`tests/cron/`、`tests/agent/test_loop_cron_timezone.py`、`tests/agent/test_heartbeat_service.py`、`tests/agent/test_evaluator.py`

**代码改点**：


| 文件                                         | 操作                                                                                                                                                                                                                                                         |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `nanobot/agent/loop.py`                    | 删 `from nanobot.agent.tools.cron import CronTool`；删 `from nanobot.cron.service import CronService`；`AgentLoop.__init__` 去掉 `cron_service` 参数；`_register_default_tools` 去掉 cron 分支；`_set_tool_context` 的遍历元组 `("spawn", "cron", "my")` 改成 `("spawn", "my")` |
| `nanobot/config/paths.py`                  | 删 `get_cron_dir`                                                                                                                                                                                                                                           |
| `nanobot/config/__init__.py`               | 导出列表去掉 `get_cron_dir`                                                                                                                                                                                                                                      |
| `nanobot/config/schema.py::DreamConfig`    | 删 `cron` 字段、`build_schedule`、`describe_schedule`；删 `interval_h` 的 `_HOUR_MS`；新增 `force_trigger_ratio: float = 0.9`                                                                                                                                         |
| `tests/config/test_dream_config.py`        | 按新 DreamConfig 字段改断言                                                                                                                                                                                                                                       |
| `tests/config/test_config_paths.py`        | 删 cron 目录相关用例                                                                                                                                                                                                                                              |
| `nanobot/agent/memory.py`                  | 注释 "heavyweight cron-scheduled" 改为 "token-threshold triggered"；按 §3 的触发策略重写 `Dream` 外层触发                                                                                                                                                                   |
| `nanobot/templates/AGENTS.md` / `TOOLS.md` | 删 cron 工具相关段落                                                                                                                                                                                                                                              |


**依赖清理**：  

- `requirements.txt` 删 `croniter>=6.0.0,<7.0.0`、`tzdata`（如果其它地方没用）。  
- `pyproject.toml` 暂无 cron 直接声明。

### 4.2 GitStore 清理清单

**删除文件**：

- `nanobot/utils/gitstore.py`
- `tests/utils/test_gitstore.py`
- `tests/agent/test_git_store.py`
- `tests/command/test_builtin_dream.py`（`/dream` 命令的 diff 渲染强依赖 git，整体删除；Dream 相关业务逻辑的测试已由 `tests/agent/test_dream.py` 覆盖）

**代码改点**：


| 文件                                                                                                  | 操作                                                                                                                                                                              |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `nanobot/agent/memory.py::MemoryStore`                                                              | 删 `self._git`、`@property git`、`_maybe_migrate_legacy_history` 里与 git 无关的保留即可                                                                                                    |
| `nanobot/agent/memory.py::Dream`                                                                    | 删 `annotate_line_ages` 参数 / `_STALE_THRESHOLD_DAYS` / `_annotate_with_ages`；Phase 1 提示词删 `stale_threshold_days`；`run()` 里删 `self.store.git.is_initialized()` + `auto_commit` 分支 |
| `nanobot/config/schema.py::DreamConfig`                                                             | 删 `annotate_line_ages` 字段                                                                                                                                                       |
| `nanobot/utils/helpers.py`                                                                          | `create_workspace_files` 里删除 `GitStore(...).init()` 那段                                                                                                                          |
| `nanobot/command/builtin.py`                                                                        | `cmd_dream` / `cmd_dream_revert` 的 git 读取分支全部简化：改成"展示 Dream 上次 analysis 文本 + 最近 N 条 history 条目"，不做 diff。具体实现可以保留命令名，但方法体改写                                                      |
| `nanobot/agent/tools/filesystem.py` / `search.py` / `skills/skill-creator/scripts/package_skill.py` | `.git` 仅作为要忽略的目录名字符串存在，保留字面量即可（那只是忽略规则）                                                                                                                                         |
| `nanobot/templates/AGENTS.md` / `TOOLS.md` / `MEMORY.md` 等                                          | 如有提"git"/"line ages"/"← Nd"的描述，一并删除或简化                                                                                                                                          |


**依赖清理**：  

- `requirements.txt` 删 `dulwich>=0.22.0,<1.0.0`。

### 4.3 其他一并清理（与后端集成无关的 CLI 残留）

`git status` 显示 CLI/API/部分 provider 已被用户删除（显示为 `D`）。本阶段顺手把 `nanobot/command/builtin.py` 里的 `cmd_restart`（调用 `os.execv`）删掉或改成 no-op，因为 `os.execv(sys.executable, ["-m", "nanobot", ...])` 在 csi-back 进程内调用会直接替换掉 FastAPI 进程，非常危险。

### 4.4 预清理验收

```powershell
# 在 .venv 里
.\.venv\Scripts\Activate.ps1
pytest -q
python .\nanobot_tester.py --message "hello"
```

要求：

- `pytest` 全绿（新删掉的模块测试自然也被移除，不是 skip）。
- `nanobot_tester.py` 单轮对话跑通，不再产生 `.git`、`cron/store.json`。

---

## 五、目标目录结构

整包迁入后，`csi-back` 长这样：

```
csi-back/
├─ app/
│  ├─ service/
│  │  ├─ nanobot/                     ← 整个 nanobot 源码（§4 清理后的版本）
│  │  │  ├─ __init__.py               ← 对外暴露 Nanobot / AgentHook 等
│  │  │  ├─ nanobot.py
│  │  │  ├─ agent/
│  │  │  │  ├─ loop.py
│  │  │  │  ├─ memory.py
│  │  │  │  ├─ context.py
│  │  │  │  ├─ runner.py
│  │  │  │  ├─ subagent.py
│  │  │  │  ├─ autocompact.py
│  │  │  │  ├─ skills.py
│  │  │  │  ├─ hook.py
│  │  │  │  └─ tools/               ← 文件工具全保留，默认不注册
│  │  │  ├─ providers/
│  │  │  ├─ session/manager.py
│  │  │  ├─ config/
│  │  │  ├─ command/
│  │  │  ├─ bus/
│  │  │  ├─ security/
│  │  │  ├─ utils/
│  │  │  ├─ skills/                  ← 源码内置 skill md（builtin）
│  │  │  ├─ templates/
│  │  │  └─ storage/                 ← 新增：存储抽象 + Mongo 实现
│  │  │     ├─ __init__.py
│  │  │     ├─ base.py               ← Protocol 定义
│  │  │     ├─ mongo_config.py
│  │  │     ├─ mongo_session.py
│  │  │     ├─ mongo_memory.py
│  │  │     └─ models.py             ← Beanie Document（nanobot_* 集合）
│  │  │
│  │  ├─ analyst/                     ← 替代旧 agent/，负责业务编排
│  │  │  ├─ __init__.py
│  │  │  ├─ service.py                ← AnalystService（启动/停止/审批/SSE）
│  │  │  ├─ tools.py                  ← get_entity / modify_entity / notify_user / write_todos
│  │  │  ├─ hooks.py                  ← StatusHook / TodosHook / ApprovalHook / ResultHook
│  │  │  ├─ context.py                ← ContextVar 绑定 thread_id / AnalystService 引用
│  │  │  ├─ prompt.py                 ← 结果格式约束、todo 提示词等
│  │  │  └─ result.py                 ← 最终 JSON 解析与兜底
│  │  └─ （旧 agent/ 目录删除）
│  │
│  ├─ models/
│  │  └─ agent/
│  │     ├─ agent.py                  ← 保留 AgentModel / AgentAnalysisSessionModel
│  │     ├─ configs.py                ← 保留 AgentModelConfigModel / AgentPromptTemplateModel
│  │     └─ checkpoint.py             ← 删除
│  │
│  ├─ api/v1/endpoints/agent.py       ← 只改 import 与 Service 类型，路由体不变
│  └─ ...
```

### 迁入注意

- `nanobot/__init__.py` 里保留 `from nanobot.nanobot import Nanobot, RunResult`，迁入后 import 路径变成 `from app.service.nanobot import Nanobot, RunResult`。需要批量改所有 `from nanobot.xxx` 为 `from app.service.nanobot.xxx`。
- 建议用一次性脚本做：`rg -l "^from nanobot\."` + `sd "from nanobot\." "from app.service.nanobot."`（或 IDE 全仓库替换）。
- `nanobot_tester.py` 继续放在 sdk 仓库根（迁入时**不**带走），改写 import 后仍可作为脚本级冒烟入口；csi-back 运行期不依赖它。

---

## 六、MongoDB 数据模型

全部以 `nanobot_` 前缀，避开 csi-back 已有命名空间。Beanie Document 定义放在 `app/service/nanobot/storage/models.py`，并在 `app/models/__init__.py::get_all_models()` 注册。

### 6.1 集合设计

```text
nanobot_configs
  _id: str                 # "global" / agent_id
  data: dict               # Config.model_dump(by_alias=True)
  updated_at: datetime

nanobot_sessions
  _id: str                 # session_key（csi-back 侧就是 thread_id）
  workspace_key: str       # agent_id
  created_at: datetime
  updated_at: datetime     # 索引 + 可做 TTL
  metadata: dict           # runtime_checkpoint / pending_user_turn / _last_summary / ...
  last_consolidated: int
  status: str              # 业务字段，可选（也可以继续由 AgentAnalysisSessionModel 独占）

nanobot_session_messages
  session_key: str         # 索引
  seq: int                 # 索引，与 session_key 复合唯一
  role: str
  content: Any             # str 或 list[dict]
  tool_calls: list | None
  tool_call_id: str | None
  name: str | None
  reasoning_content: str | None
  thinking_blocks: list | None
  timestamp: datetime
  injected_event: str | None
  subagent_task_id: str | None
  extras: dict             # 兜底

nanobot_memory_docs
  _id: str                 # f"{workspace_key}:{filename}"（filename ∈ MEMORY.md/SOUL.md/USER.md）
  workspace_key: str       # 索引
  filename: str
  content: str
  updated_at: datetime

nanobot_history
  workspace_key: str       # 索引
  cursor: int              # 与 workspace_key 复合唯一，单调递增
  timestamp: datetime
  content: str

nanobot_history_state
  _id: str                 # workspace_key
  last_cursor: int
  last_dream_cursor: int
  updated_at: datetime
```

### 6.2 索引

```python
IndexModel([("session_key", ASCENDING), ("seq", ASCENDING)], unique=True)
IndexModel([("workspace_key", ASCENDING), ("cursor", ASCENDING)], unique=True)
IndexModel([("workspace_key", ASCENDING)])
IndexModel([("updated_at", ASCENDING)])  # 如需 TTL 可加 expireAfterSeconds
```

### 6.3 为什么不用 messages 内嵌数组

会话消息会随对话增长（单次分析 agent 可能产生数百条 tool call/result），内嵌会碰到 16MB 上限；并且 `AgentLoop._save_turn` 是增量 append，独立集合更自然。`SessionManager` 内仍然把 messages 装到 `Session.messages: list[dict]` 给 `ContextBuilder` 用，只是读写由 Mongo backend 承担。

---

## 七、分阶段实施路径

### 阶段 0：预清理（sdk 仓库内）

见 §4。产出：干净的 nanobot 代码库，跑通 `pytest` 与 `nanobot_tester.py`。

### 阶段 1：整包迁入 csi-back

1. 拷贝 `nanobot/` → `csi-back/app/service/nanobot/`。
2. 全仓库 import 替换 `from nanobot.` → `from app.service.nanobot.`。
3. 合并依赖到 csi-back 的 `requirements.txt` / `pyproject.toml`：
  - 新增：`loguru`、`tiktoken`、`jinja2`、`pypdf`、`python-docx`、`openpyxl`、`python-pptx`、`json-repair`、`chardet`、`readability-lxml`、`filelock`、`mcp`、`ddgs`、`openai`、`anthropic`、`langfuse`（按 csi-back 实际需要裁剪；web 工具禁用后 `ddgs/readability-lxml` 可不要）。
  - 注意 `anthropic` / `openai` 如果 csi-back 已有就对齐版本。
4. **不要**拷贝 `nanobot_tester.py`、`pyproject.toml`、`requirements*.txt`、`tests/`；这些留在 sdk 仓库作参考。tests 的迁移见阶段 6。
5. 在 csi-back 的 `.venv` 里 `pip install -r requirements.txt` 验证不报 import 错误。
6. 暂时不接入业务，先写一个最小脚本跑通 `Nanobot.from_config(config_path=".../config.json")` + `await bot.run("hello")`，确认 import 路径全改对、文件存储依然工作（这一步仍用文件系统，不碰数据库）。

**产出**：`app/service/nanobot/` 可以脱离 csi-back 其他部分独立实例化。

### 阶段 2：抽象存储 backend + Mongo 实现

这一步**不动业务**，只把 §2.1 清单里的文件 I/O 改可插拔。

#### 2.1 定义 Protocol（`app/service/nanobot/storage/base.py`）

```python
class ConfigStore(Protocol):
    async def load(self, key: str = "global") -> dict | None: ...
    async def save(self, key: str, data: dict) -> None: ...

class SessionStore(Protocol):
    async def load(self, key: str) -> Session | None: ...
    async def save(self, session: Session) -> None: ...
    async def list(self) -> list[dict]: ...
    async def invalidate(self, key: str) -> None: ...  # 内存缓存失效，默认 no-op

class MemoryBackend(Protocol):
    async def read_doc(self, ws: str, filename: str) -> str: ...
    async def write_doc(self, ws: str, filename: str, content: str) -> None: ...
    async def append_history(self, ws: str, entry: str) -> int: ...
    async def read_unprocessed_history(self, ws: str, since_cursor: int) -> list[dict]: ...
    async def compact_history(self, ws: str, max_entries: int) -> None: ...
    async def get_cursors(self, ws: str) -> tuple[int, int]: ...  # (last_cursor, last_dream_cursor)
    async def set_dream_cursor(self, ws: str, cursor: int) -> None: ...
```

> `SessionManager` 当前接口是同步的（`get_or_create/save`），但 `AgentLoop` 使用时已经在协程上下文。**改造时把 `SessionManager.save/_load/list_sessions` 一次性改 async**，对应调用点统一 `await`。这是本期工作量最大的一处改动。

#### 2.2 改 nanobot 内部调用链

- `nanobot/config/loader.py`：`load_config` / `save_config` 改为接收 `store: ConfigStore`。保留旧的文件路径实现作为 `FileConfigStore`，并新增 `MongoConfigStore`。
- `nanobot/session/manager.py::SessionManager`：`_load` / `save` 委托给 `store`；`_cache` 保留（内存层 LRU 无所谓）；所有读写改 async。
- `nanobot/agent/memory.py::MemoryStore`：所有 `.read_text` / `.write_text` / `open(...).write` 改走 `backend`；`_cursor_file` / `_dream_cursor_file` 改成 `backend.get_cursors / set_dream_cursor`；`append_history` 改 async。
- `nanobot/agent/loop.py`：`_save_turn` / `consolidator.maybe_consolidate_by_tokens` / `_schedule_background` 的调用点统一走 async。
- `nanobot/agent/context.py::ContextBuilder`：`build_system_prompt` 里 `self.memory.read_memory()` 等也要改 async（或让 ContextBuilder 自己缓存"一次对话期内的 memory snapshot"，减少阻塞）。**推荐后者**：`ContextBuilder.refresh_memory_snapshot()` 在 `_process_message` 入口先 await 一次，后续同步读快照。

#### 2.3 Beanie Document 与实现

- `storage/models.py`：按 §6 定义 7 个 Document。
- `storage/mongo_config.py` / `mongo_session.py` / `mongo_memory.py`：直白的 CRUD 封装。
- `app/models/__init__.py::get_all_models()`：把 7 个新 Document 加进列表，旧的 `CheckpointModel` / `CheckpointWriteModel` 删掉。

#### 2.4 `Nanobot` 入口

新增构造器：

```python
class Nanobot:
    @classmethod
    def from_components(
        cls,
        config: Config,
        *,
        session_store: SessionStore,
        memory_backend: MemoryBackend,
        workspace_key: str,                    # = agent_id
    ) -> "Nanobot":
        ...
```

保留 `from_config` 做本地脚本冒烟用（默认 file backend）。

**产出**：`Nanobot.from_components(...)` 能用 MongoDB 跑一条会话，消息/记忆/历史落到 Mongo。文件系统完全不使用。

### 阶段 3：业务 Service 层

在 `app/service/analyst/` 里重建 LangChain 版的全部业务能力。

#### 3.1 AnalystService（`service.py`）

替换旧 `AgentService` 的所有 classmethod，接口兼容：

```python
class AnalystService:
    _bots: dict[str, Nanobot] = {}          # key = agent_id
    _bots_lock = asyncio.Lock()
    sse_subscribers: dict[str, list[asyncio.Queue]] = {}
    sse_lock = asyncio.Lock()
    running_tasks: dict[str, asyncio.Task] = {}
    task_lock = asyncio.Lock()
    cancel_reasons: dict[str, str] = {}
    pending_resumes: dict[str, asyncio.Queue] = {}

    @classmethod
    async def get_or_build_bot(cls, agent: AgentModel, model: AgentModelConfigModel) -> Nanobot: ...
    @classmethod
    async def start_agent(cls, system_prompt, user_prompt, agent_template, model_config, data) -> str: ...
    @classmethod
    async def run_analysis(cls, thread_id, bot, user_prompt): ...
    @classmethod
    async def broadcast_sse(cls, thread_id, payload): ...
    @classmethod
    def sse_event(cls, type, data) -> dict: ...
```

- `get_or_build_bot`：按 `agent_id` 缓存；miss 时：
  1. 从 `AgentModelConfigModel` 取 `base_url/api_key/model`，合并 `AgentModel.llm_config`（temperature 等）。
  2. 构造 `Config`，设 `providers.openai_compat.api_key/api_base`、`agents.defaults.model`。
  3. `Nanobot.from_components(config, session_store=mongo_session_store, memory_backend=mongo_memory_backend, workspace_key=agent_id)`。
  4. 注入 hooks + 业务工具（见 3.2/3.3）。

#### 3.2 Hooks（`hooks.py`）

- `StatusHook`：`before_execute_tools` / `after_iteration` 里把 step 写入 `AgentAnalysisSessionModel.steps` 并 SSE 广播 `status`。
- `TodosHook`：响应 `write_todos` 工具调用结果，把新 todos 同步到 `AgentAnalysisSessionModel.todos`。
- `ApprovalHook`：在工具执行之前不能 skip（nanobot 没提供原生接口），**审批逻辑放进工具本身**（见 3.3），Hook 只负责 SSE 的 `approval_required` 广播与 `pending_approval` 字段清理。
- `ResultHook`：`on_run_complete`（或读 `RunResult.content`）里解析最终 JSON → `ResultPayloadSchema`；广播 `result`；落到 `AgentAnalysisSessionModel.result`。

#### 3.3 业务工具（`tools.py`）

用 nanobot `BaseTool`（见 `nanobot/agent/tools/base.py`）重写：


| 工具                 | 说明                                                                                                                                                                                                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_current_time` | 直接返回时间字符串，无状态。                                                                                                                                                                                                                                                            |
| `get_entity`       | 从 `contextvars` 拿不到可以省略 thread_id；直接复用 `get_es()`。                                                                                                                                                                                                                        |
| `modify_entity`    | **在 `execute()` 里完成审批握手**：`contextvars` 取 `thread_id` → 更新 `AgentAnalysisSessionModel.status=awaiting_approval` + `pending_approval=payload` → SSE `approval_required` → `await AnalystService.pending_resumes[thread_id].get()` → 按决策走 approve/reject 分支。无需改 nanobot 核心。 |
| `notify_user`      | SSE 广播 `message`；`thread_id` 也从 `contextvars` 拿。                                                                                                                                                                                                                          |
| `write_todos`      | 参数 `todos: list[{content, status}]`；写 `AgentAnalysisSessionModel.todos` + SSE `status`。                                                                                                                                                                                   |


`thread_id` 注入方式：`app/service/analyst/context.py` 定义 `current_thread_id: ContextVar[str]`，`AnalystService.run_analysis` 在 await `bot.run(...)` 外层 `token = current_thread_id.set(thread_id)`，finally 里 reset。

#### 3.4 系统提示装配（`prompt.py`）

- `TODO_MIDDLEWARE_SYSTEM_PROMPT` / `TOOL_DESCRIPTION` / `RESULT_FORMAT_INSTRUCTION` 平移。
- Agent 的最终 system prompt = `AgentPromptTemplateModel.system_prompt` + todo 段 + 结果格式段。
- 初期直接在 `AnalystService.start_agent` 拼好后塞进 `Config.agents.defaults` 是不行的（nanobot 的 system prompt 来自 `ContextBuilder` + workspace 里 `AGENTS.md`）。两个选择：
  - **A. 覆盖方案**：在 `ContextBuilder.build_system_prompt` 追加一个 `extra_system_suffix`；AnalystService 启动时设置。
  - **B. 首条 user 消息注入**：把业务 system 文本拼在 user_prompt 前面。鲁棒性差，跳过。
- 推荐 A，改动量小。

#### 3.5 结构化结果（`result.py`）

- 优先走 provider 的 `response_format: json_schema`（OpenAI 兼容）：在 `OpenAICompatProvider.chat_with_retry` 现有 `extra_kwargs` 透传路径上，`AnalystService` 构造时传 `response_format={"type":"json_schema","json_schema":{"name":"result","schema": ResultPayloadSchema.model_json_schema(), "strict": True}}`。
- 不支持的 provider 兜底：`json_repair.loads(RunResult.content)` → `ResultPayloadSchema(**parsed)`；失败填 `summary=raw, success=False, failure_reason="格式异常"`。

### 阶段 4：路由切换

- `app/api/v1/endpoints/agent.py`：只需要改两处 import（`AgentService` → `AnalystService`）即可，接口行为不变。
- SSE `/agent/status` 的订阅/分发逻辑保持不变（`AnalystService.sse_subscribers` 与旧同名）。
- `/agent/approve` 的 `pending_resumes[thread_id].put_nowait(...)` 由新的 `modify_entity` 工具端消费。

### 阶段 5：彻底移除 LangChain

- 删文件：`app/service/agent/agent.py`、`app/service/agent/tools.py`、`app/service/agent/motor_checkpinter.py`、`app/models/agent/checkpoint.py`、`app/service/agent/__init__.py`（若无其它引用），最后删除 `app/service/agent/` 目录。
- `app/models/__init__.py` 去掉 `CheckpointModel` / `CheckpointWriteModel`。
- `app/utils/agent.py` 里的 `parse_approval_decision`、`modify_entity_approval_description`、`normalize_todo`、`update_session_status`、`get_step_detail`、`inject_template_fields`：保留（`AnalystService` 还会用到）；删除只服务 langchain 的部分（如果有）。
- MongoDB 侧 drop 旧集合：`agent_checkpointer`、`agent_checkpointer_writes`。`agent_analysis_sessions` **保留**（模型同名，向前兼容即可；本期用户说允许数据重置）。
- requirements：删 `langchain`* / `langgraph*`。

### 阶段 6：测试迁移与回归

- sdk 仓库里保留的单元测试中，有用的迁进 `csi-back/tests/nanobot/`：
  - `tests/agent/test_runner.py`、`test_consolidator.py`、`test_consolidate_offset.py`、`test_dream.py`、`test_memory_store.py`、`test_session_manager_history.py`、`test_auto_compact.py`、`test_hook_composite.py`、`test_runner.py`、`test_context_documents.py` 这些核心逻辑测试改 async + mock storage 后迁移。
  - Provider 相关测试按需迁移。
  - cron/git/heartbeat/evaluator 相关测试整体丢弃（已在阶段 0 清理）。
- 新增 csi-back 侧集成测试：`tests/agent/test_analyst_flow.py` 覆盖 `/agent/start -> SSE -> /agent/approve -> SSE:result` 全链路（pytest-asyncio + httpx.AsyncClient + mongomock/真实 mongo）。

---

## 八、关键技术点补充说明

### 8.1 SessionManager 同步→异步

现状：`SessionManager.get_or_create / save / _load` 是同步的；`AgentLoop._save_turn` 在 tool loop 热路径里同步调用 `self.sessions.save(session)`。

改造后这些调用都要 `await`。影响点（grep `self.sessions.save` / `self.sessions.get_or_create`）：

- `nanobot/agent/loop.py`：约 10+ 处。
- `nanobot/agent/autocompact.py::AutoCompact.prepare_session / check_expired`。
- `nanobot/command/builtin.py::cmd_status` 等命令处理器。
- `nanobot/agent/memory.py::Consolidator.maybe_consolidate_by_tokens`。

`check_expired` 当前被 `AgentLoop.run()` 主循环调用（非 async 回调），改造方案：

- csi-back 里我们不跑 `AgentLoop.run()` 这个 bus 主循环，而是直接用 `process_direct` / `bot.run()` 单次调用。`check_expired` 这条路径本期**可以不管**（等到需要多会话 TTL 时再做）。
- 直接删除 `AgentLoop.run()` 整个方法，让这个类只服务"一次 run 一条请求"模式（csi-back 不需要 bus + 主循环）。

### 8.2 `AgentLoop` 的 Bus/主循环是否保留

`AgentLoop.run()` + `_dispatch()` 用 `MessageBus` 做异步队列，是给 CLI/IM 等场景用的；csi-back 的 agent 是 per-request、短生命周期，不需要消息总线。

方案：

- 保留 `MessageBus` 类（`nanobot/bus/queue.py`），`process_direct` 内部仍用它发事件。
- 删除 `AgentLoop.run()` / `_dispatch()` / `_pending_queues` 路由（它们服务 bus 主循环）；保留 `_process_message` / `process_direct`。
- 删除 `nanobot/command/builtin.py::cmd_stop` / `cmd_restart`；`cmd_status` 可保留，但不再被 slash 触发，改成 `AnalystService` 内部的诊断 helper。

### 8.3 取消/暂停/恢复

- 取消：`task.cancel()`；`_process_message` 的 `asyncio.CancelledError` 分支已经做了 runtime_checkpoint 的持久化，因此下一次同 `session_key` 进来会自动恢复——只要 Mongo session store 工作正常。
- 暂停：业务上等同于取消 + 设置 `status=paused`；下次调 `/agent/start?thread_id=...` 用同 thread_id 即可恢复。
- 恢复接口：需要新增一个"续跑"路由（或复用 `/agent/start` 支持传 `thread_id` 不传 `entity_uuid`）。本期**不做**，作为后续迭代。本期 `cancel_reasons=='pause'` 仍写 `status=paused`，前端展示静态，要重跑需要用户手动发起新任务。

### 8.4 Context 上下文估算 + Dream 强制触发

```python
# nanobot/agent/memory.py::Dream
async def maybe_force_run(self, session) -> bool:
    prompt_tokens, _ = self._consolidator.estimate_session_prompt_tokens(session)
    dream_prompt_tokens = self._cached_dream_prompt_tokens()      # 预 tokenize 一次
    threshold = int(self._context_window_tokens * self._force_trigger_ratio)
    if prompt_tokens + dream_prompt_tokens < threshold:
        return False
    if not self.store.read_unprocessed_history(...):
        return False
    await self.run()
    return True
```

调用点：`AgentLoop._process_message` 在 `await self.consolidator.maybe_consolidate_by_tokens(session, ...)` 之后再 `await self.dream.maybe_force_run(session)`（让 Consolidator 先把消息压进 history，再让 Dream 把 history 整理到 MEMORY）。

### 8.5 Skills 只读 builtin

阶段 0 清理后 `nanobot/skills/` 仅剩非 cron 的源码 md。`SkillsLoader` 改动：

- `__init__` 不再接收 workspace skills 目录（只留 builtin）。
- `list_skills` / `load_skill` 只扫 builtin。
- `workspace_skills` 属性删除。
- `Dream._build_tools` 里 `WriteFileTool(allowed_dir=skills_dir)` 的"允许 Dream 写 workspace skills"这条分支**本期去掉**（Dream 只写 MEMORY/SOUL/USER）。这里要同时更新 Phase 2 提示词模板去掉 skill 写入指令。

---

## 九、风险与回滚


| 风险                                                      | 缓解                                                                                                      |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `SessionManager` 改 async 引发大面积调用点修改                     | 每改一个文件就跑 `pytest tests/agent/` 定点回归，最后全量跑                                                               |
| Dream 强制触发引入额外 LLM 延迟                                   | 设上限 `max_batch_size=10`；`force_trigger_ratio` 可 per-agent 调                                             |
| OpenAI 兼容 provider 对 `response_format=json_schema` 支持不一 | 按 provider spec 判定；不支持时 fallback 文本 + `json_repair`                                                     |
| MongoDB 大量小文档写入压力                                       | 开 connection pool（csi-back 已有 `maxPoolSize=50`）；`session_messages` 按 `(session_key, seq)` 复合索引，单会话写入量可控 |
| 旧 LangChain 集合残留                                        | 阶段 5 里显式 drop，文档里列出命令                                                                                   |
| 迁移期线上不可用                                                | 迁移在 feature branch 进行，合并前灰度跑 `/agent/start` 压测                                                          |


回滚策略：阶段 0/1/2 都在独立 feature 分支；阶段 4 切路由前保留 `AgentService` 原文件直到下一个 sprint。一旦出问题，revert 到阶段 4 之前即可。

---

## 十、验收标准

本期完成条件：

1. `csi-back` 启动时仅依赖 MongoDB / ES / Redis / MariaDB / RabbitMQ（与现状一致），**不**写任何 nanobot 相关文件（`~/.nanobot`、`workspace/`、`memory/`、`skills/` 都不出现）。
2. `POST /agent/start` → 走 nanobot agent → SSE 正常推送 `status / approval_required / message / result`。
3. `POST /agent/approve` 能让 `modify_entity` 按决策继续或拒绝。
4. `AgentAnalysisSessionModel` 在 MongoDB 中能看到 `steps / todos / pending_approval / result` 正确更新。
5. 同一 `agent_id` 跨两次 `/agent/start` 能看到 `nanobot_memory_docs` 累积（即 agent 级记忆生效）。
6. 删除了所有 langchain / langgraph / cron / git / heartbeat / evaluator 代码与依赖。

---

## 十一、TODO（建议拆成独立 commit 的颗粒度）


| #   | 内容                                                                        | 阶段   | 预估影响文件数 |
| --- | ------------------------------------------------------------------------- | ---- | ------- |
| 1   | 清理 cron 模块、工具、测试、skill、模板、依赖                                              | 阶段 0 | ~20     |
| 2   | 清理 GitStore、Dream 注释与 `annotate_line_ages`、dulwich 依赖                     | 阶段 0 | ~10     |
| 3   | 清理 heartbeat、evaluator、`cmd_restart`                                      | 阶段 0 | ~8      |
| 4   | 清理后回归：`pytest` + `nanobot_tester.py`                                      | 阶段 0 | 0       |
| 5   | nanobot → `csi-back/app/service/nanobot/` 整包拷贝 + import 替换                | 阶段 1 | all     |
| 6   | 合并 python 依赖到 csi-back                                                    | 阶段 1 | 1       |
| 7   | 定义 storage Protocol + 抽出 File 默认实现                                        | 阶段 2 | ~5      |
| 8   | Beanie Document + Mongo 实现（Config/Session/Memory）                         | 阶段 2 | ~6      |
| 9   | `SessionManager` / `MemoryStore` / `ContextBuilder` / `AgentLoop` 改 async | 阶段 2 | ~15     |
| 10  | 删除 `AgentLoop.run/_dispatch` 主循环与 slash 命令不需要的分支                          | 阶段 2 | ~3      |
| 11  | Dream 改阈值触发 + `DreamConfig` 字段调整                                          | 阶段 2 | ~3      |
| 12  | `app/service/analyst/` 业务层（Service + Hooks + Tools + Context）             | 阶段 3 | ~8      |
| 13  | 结构化结果 & response_format 接入                                                | 阶段 3 | ~3      |
| 14  | 路由切换 `app/api/v1/endpoints/agent.py`                                      | 阶段 4 | 1       |
| 15  | 删除 langchain/langgraph、旧 Service、Checkpoint 模型与集合                         | 阶段 5 | ~6      |
| 16  | 新增 / 迁移核心单测                                                               | 阶段 6 | ~10     |


---

*最后更新：迁移开始前；实施过程中请同步更新各阶段完成情况。*