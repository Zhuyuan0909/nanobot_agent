# System Prompt 组装机制分析 — nanobot 内置 vs workspace 自定义

## 核心结论

**nanobot 的原生内置 skill 和工具都会被加载**，你的 workspace 组件是叠加在上面，不是替换。同名时 workspace 优先覆盖。

---

## System Prompt 的完整组装结构

System Prompt 由 `ContextBuilder.build_system_prompt()`（`nanobot/agent/context.py`）组装，各 section 用 `\n\n---\n\n` 分隔，共 6 个 section：

```
┌──────────────────────────────────────────────────┐
│ Section 1: Identity（nanobot 内置，必定加载）       │
│   来自 nanobot/templates/agent/identity.md        │
│   内容：运行时信息、workspace 路径、平台策略、       │
│   搜索指导、untrusted content 警告、message 指令    │
├──────────────────────────────────────────────────┤
│ Section 2: Bootstrap Files（workspace，可选）      │
│   AGENTS.md + SOUL.md + USER.md + TOOLS.md        │
│   文件不存在则跳过                                  │
├──────────────────────────────────────────────────┤
│ Section 3: Memory（workspace，可选）               │
│   memory/MEMORY.md，若为模板内容则抑制              │
├──────────────────────────────────────────────────┤
│ Section 4: Always Skills（nanobot + workspace）   │
│   所有 always: true 的 skill 全文注入              │
│   ★ nanobot 内置了 memory 和 my 两个 always skill │
│   ★ workspace 的 skill 同名会覆盖内置 skill        │
├──────────────────────────────────────────────────┤
│ Section 5: Skills Summary（nanobot + workspace）  │
│   所有可用 skill 的摘要列表（排除已全文注入的）      │
├──────────────────────────────────────────────────┤
│ Section 6: Recent History（workspace，可选）       │
│   memory/history.jsonl 最近 50 条                  │
└──────────────────────────────────────────────────┘
```

---

## Section 详解

### Section 1: Identity（nanobot 内置）

来源：`nanobot/templates/agent/identity.md`（Jinja2 模板），包含：

- **Runtime 块**：OS 信息、Python 版本
- **Workspace 块**：告知 Agent workspace 路径、MEMORY.md 位置、history.jsonl 位置、自定义 skill 目录
- **Platform Policy**：来自 `nanobot/templates/agent/platform_policy.md`，区分 Windows/POSIX 平台
- **Format Hint**：针对 telegram/qq/discord/whatsapp/sms/email/cli 等不同渠道的条件格式提示
- **Search & Discovery**：指导 Agent 优先使用 `grep`/`glob` 而非 `exec`，包含 `output_mode="count"` 用法，以及 untrusted content 警告（web 内容不可信）
- **Message Tool 指令**：告知 Agent 用 `message` 工具发送文件，而非 `read_file`

### Section 2: Bootstrap Files（workspace）

`ContextBuilder.BOOTSTRAP_FILES` 定义为 `["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md"]`。

逐一从 `{workspace}/{filename}` 加载，文件不存在则跳过，不报错。

### Section 3: Memory（workspace）

从 `workspace/memory/MEMORY.md` 读取，前缀加 `# Memory`。

但如果内容与 `nanobot/templates/memory/MEMORY.md` 模板完全一致（用户未自定义），则抑制不注入。

### Section 4: Always Skills（nanobot + workspace）

`SkillsLoader.get_always_skills()` 返回所有 `frontmatter` 中 `always: true` 的 skill，来自两个目录：

| 来源 | 路径 |
|---|---|
| nanobot 内置 | `nanobot/skills/` |
| workspace | `workspace/skills/` |

nanobot 内置的两个 always skill：
- **memory** — 教 Agent 如何管理 SOUL.md、USER.md、MEMORY.md、history.jsonl
- **my** — 教 Agent 如何使用 `my` 工具进行运行时自检

注入格式：
```
### Skill: <name>

<Markdown 正文>
```

### Section 5: Skills Summary（nanobot + workspace）

模板来自 `nanobot/templates/agent/skills_section.md`。

列出所有可用 skill 的名称、描述、文件路径、可用状态（排除 Section 4 已全文注入的 skill）。供 LLM 按需 `read_file` 加载。

### Section 6: Recent History（workspace）

`MemoryStore.read_unprocessed_history()` 从 `workspace/memory/history.jsonl` 读取自上次 Dream 游标以来的最近 50 条记录。

格式：
```
# Recent History
- [timestamp] content
- [timestamp] content
```

---

## 工具注册的完整组成

工具在 `AgentLoop.__init__()` 和 `AgentLoop._register_default_tools()`（`nanobot/agent/loop.py`）中注册。

### 必定注册的内置工具（nanobot）

| 工具 | 类 | 来源文件 |
|---|---|---|
| `read_file` | ReadFileTool | `tools/filesystem.py` |
| `write_file` | WriteFileTool | `tools/filesystem.py` |
| `edit_file` | EditFileTool | `tools/filesystem.py` |
| `list_dir` | ListDirTool | `tools/filesystem.py` |
| `glob` | GlobTool | `tools/search.py` |
| `grep` | GrepTool | `tools/search.py` |
| `notebook_edit` | NotebookEditTool | `tools/notebook.py` |
| `message` | MessageTool | `tools/message.py` |
| `spawn` | SpawnTool | `tools/spawn.py` |

### 条件注册的内置工具（nanobot）

| 工具 | 注册条件 |
|---|---|
| `exec` | `exec_config.enable = true` |
| `web_search` | `web_config.enable = true` |
| `web_fetch` | `web_config.enable = true` |
| `cron` | 提供了 CronService 实例 |
| `my` | `tools_config.my.enable = true`（默认开启） |

### MCP 工具（workspace config.json 配置）

`AgentLoop._connect_mcp()` 在启动时调用 `connect_mcp_servers()`（`tools/mcp.py`），对每个 MCP 服务器：

1. 启动子进程（stdio 模式）或连接 WebSocket
2. 发送 JSON-RPC `initialize` 和 `tools/list` 发现工具
3. 包装为 `mcp_{server_name}_{tool_name}`
4. 注册到 ToolRegistry

你的 `ticket_server.py` 的 5 个工具注册后：
- `mcp_ticket_create_ticket`
- `mcp_ticket_get_ticket`
- `mcp_ticket_list_user_tickets`
- `mcp_ticket_update_ticket`
- `mcp_ticket_submit_feedback`

ToolRegistry 排序规则：**内置工具排在前面，MCP 工具排在后面**，稳定的前缀有助于 prompt caching。

---

## Skill 发现机制：workspace 优先覆盖

`SkillsLoader.list_skills()`（`nanobot/agent/skills.py:51-64`）的关键逻辑：

1. 先扫描 `workspace/skills/` → 加载所有 workspace skill
2. 记录已加载的 skill 名称
3. 再扫描 `nanobot/skills/` → 加载内置 skill
4. **如果内置 skill 的名称已在 workspace 中出现，跳过**

### 对你的项目意味着什么

你的 workspace 有 `skills/memory/SKILL.md`，nanobot 内置也有 `memory` skill：

- ✅ 你的 `memory` skill **完全覆盖** nanobot 内置的 `memory` skill
- ✅ nanobot 内置的其他 skill 照常加载（`my`, `weather`, `github`, `cron`, `summarize`, `tmux`, `skill-creator`, `clawhub`）

---

## 你的项目的实际组装效果

### System Prompt 最终内容

| 内容 | 来源 | 是否加载 |
|---|---|---|
| Identity 模板（运行时、平台策略、搜索指导） | nanobot 内置 | ✅ 必定 |
| AGENTS.md | workspace | ✅ |
| SOUL.md | workspace | ✅ |
| USER.md | workspace | ✅ |
| TOOLS.md | workspace | ✅ |
| MEMORY.md（用户记忆） | workspace | ✅ |
| memory SKILL.md（全文） | workspace | ✅（覆盖内置） |
| my SKILL.md（全文） | nanobot 内置 | ✅ |
| faq SKILL.md（全文） | workspace | ✅ |
| ticket SKILL.md（全文） | workspace | ✅ |
| Skills 摘要（weather, github, cron 等） | nanobot 内置 | ✅ |
| history.jsonl 近期条目 | workspace | ✅ |

### 最终工具列表

| 工具 | 来源 |
|---|---|
| read_file, write_file, edit_file, list_dir | nanobot 内置 |
| glob, grep | nanobot 内置 |
| message, spawn, my | nanobot 内置 |
| web_search, web_fetch | nanobot 内置（条件） |
| exec | nanobot 内置（条件） |
| **mcp_ticket_create_ticket** | **你的 MCP Server** |
| **mcp_ticket_get_ticket** | **你的 MCP Server** |
| **mcp_ticket_list_user_tickets** | **你的 MCP Server** |
| **mcp_ticket_update_ticket** | **你的 MCP Server** |
| **mcp_ticket_submit_feedback** | **你的 MCP Server** |

---

## 内置 Skill 完整清单

位于 `nanobot/skills/`：

| Skill | always | 备注 |
|---|---|---|
| **memory** | Yes | 你的 workspace 同名 skill 已覆盖 |
| **my** | Yes | 运行时自检工具使用指南 |
| cron | No | 定时任务管理 |
| weather | No | 需要 `curl` |
| github | No | 需要 `gh` CLI |
| summarize | No | 需要 `summarize` binary |
| tmux | No | 需要 `tmux`，仅 macOS/Linux |
| clawhub | No | 需要 Node.js / npx |
| skill-creator | No | 创建新 skill 的指南 |

---

## 一句话总结

nanobot 的内置 skill 和工具是**"打底"的**，你的 workspace 组件是**叠加的增量**。这不是二选一，而是**叠加 + 按优先级覆盖**——你 workspace 里的同名 skill 会覆盖内置版本，其余内置组件照常加载。
