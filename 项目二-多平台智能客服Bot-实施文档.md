# 项目二：多平台智能客服 Bot — 实施文档

> 基于 nanobot 框架，实现个人使用的多平台智能客服系统。
> 实施日期：2026-05-19 ~ 2026-05-21

---

## 一、项目背景与需求

### 1.1 项目定位

**个人使用、单用户、多平台**的智能客服 Bot。同一用户在飞书和钉钉上与 Bot 对话，Bot 共享记忆和上下文。

### 1.2 功能矩阵

| 功能 | 描述 | 飞书 | 钉钉 |
|------|------|------|------|
| FAQ 查询 | 知识库匹配回答产品问题 | ✅ | ✅ |
| 工单创建 | FAQ 无匹配时自动创建工单 | ✅ | ✅ |
| 工单查询 | 查看工单状态和详情 | ✅ | ✅ |
| 用户记忆 | 记住用户信息和历史问题 | ✅ | ✅ |
| 问题升级 | 转人工客服，含 SLA 分级 | ✅ | ✅ |
| 满意度评价 | 工单解决后收集用户反馈 | ✅ | ✅ |

### 1.3 用户故事

> 作为一个产品用户，我希望在飞书/钉钉中直接 @客服Bot 提问，它能基于知识库快速回答。如果问题解决不了，自动帮我创建工单并告知工单号。下次我再找它时，它还记得我之前的问题。严重问题可以转人工处理。

---

## 二、设计过程

### 2.1 前期调研

实施前对 nanobot 框架进行了完整的源码级调研，关键发现：

| 调研模块 | 文件 | 结论 |
|----------|------|------|
| Channel 机制 | `nanobot/channels/feishu.py`, `dingtalk.py` | 框架原生支持飞书/钉钉，WebSocket 长连接，无需公网 IP |
| 消息总线 | `nanobot/bus/events.py`, `queue.py` | InboundMessage/OutboundMessage + asyncio.Queue 解耦 |
| Channel 管理 | `nanobot/channels/manager.py` | ChannelManager 自动发现、启动、重试、分发 |
| Skills 系统 | `nanobot/agent/skills.py` | YAML frontmatter + Markdown 正文，支持 always/requires |
| Memory 系统 | `nanobot/agent/memory.py` | MEMORY.md + history.jsonl，Consolidator + Dream 三层记忆 |
| MCP 客户端 | `nanobot/agent/tools/mcp.py` | stdio 子进程方式连接，自动注册为 mcp_{server}_{tool} |
| Context 构建 | `nanobot/agent/context.py` | SOUL.md → AGENTS.md → Bootstrap → Memory → Skills → History |

### 2.2 关键设计决策

#### 决策一：不使用 Flask 消息路由

文档教程中的 `message_router.py` 使用 Flask Webhook 接收多平台消息。但 nanobot 的 `ChannelManager` + `MessageBus` 已经原生处理多平台消息路由，且使用各平台的原生 WebSocket，无需公网 IP。

**结论：直接使用 `nanobot gateway` 模式。**

#### 决策二：单用户 + unified_session

个人使用场景，同一用户跨飞书和钉钉。开启 `unifiedSession: true`，所有平台的 session key 统一为 `unified:default`，记忆和上下文集于一体。

#### 决策三：记忆系统双轨制

Dream（自动整理）+ skill 手动即时捕获 互补：
- **skill** — 对话中遇到关键信息，立即 `edit_file` 写入 MEMORY.md
- **Dream** — 每 2 小时分析 history.jsonl，去重、整理、发现可复用 skill

#### 决策四：MCP Server 使用原始 JSON-RPC

nanobot 的 MCP SDK 版本敏感。采用原始 JSON-RPC over stdio 实现更稳定。

**关键坑点：所有日志必须输出到 stderr，否则 stdout 污染 JSON-RPC 通道。**

#### 决策五：知识库使用 Markdown + grep

FAQ 条目在百条以内，不需要向量数据库。直接用 Markdown 文件配合 grep 工具检索。

#### 决策六：SQLite 作为工单数据库

零配置、文件级存储，适合原型和个人使用。

---

## 三、架构设计

### 3.1 系统架构

```
┌──────────────────────────────────────────────────────┐
│                多平台智能客服系统（单用户）              │
│                                                       │
│  ┌──────────┐  ┌──────────┐                          │
│  │   飞书    │  │   钉钉    │   ← 同一用户，两个平台      │
│  └─────┬────┘  └─────┬────┘                          │
│        │              │                               │
│        ▼              ▼                               │
│  ┌──────────────────────────────────────────┐        │
│  │       nanobot ChannelManager              │        │
│  │  (feishu.py / dingtalk.py)               │        │
│  └────────────────┬─────────────────────────┘        │
│                   │                                   │
│                   ▼                                   │
│  ┌──────────────────────────────────────────┐        │
│  │     MessageBus (异步队列)                  │        │
│  └────────────────┬─────────────────────────┘        │
│                   │                                   │
│                   ▼                                   │
│  ┌──────────────────────────────────────────┐        │
│  │         AgentLoop (unified_session)        │        │
│  │                                            │        │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐   │        │
│  │  │FAQ Skill │ │Ticket    │ │Memory    │   │        │
│  │  │(grep)    │ │Skill     │ │Skill     │   │        │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘   │        │
│  │       │             │            │         │        │
│  │       ▼             ▼            ▼         │        │
│  │  ┌──────────┐ ┌───────────┐ ┌─────────┐  │        │
│  │  │ 知识库    │ │ticket MCP │ │MEMORY.md│  │        │
│  │  │ *.md     │ │(SQLite)   │ └─────────┘  │        │
│  │  └──────────┘ └───────────┘              │        │
│  └──────────────────────────────────────────┘        │
│                                                       │
│  ┌──────────────────────────────────────────┐        │
│  │  Dream (每 2h): history.jsonl → 去重/整理  │        │
│  └──────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
用户消息 → Channel(平台格式解析) → InboundMessage → MessageBus
    → AgentLoop(读 MEMORY.md → 分类 → 查FAQ/建工单/升级/评价)
    → OutboundMessage → MessageBus → Channel(平台格式转换) → 用户
```

---

## 四、新增/修改的文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `workspace/config.json` | 新增 | 单用户多平台配置：deepseek + unifiedSession + 飞书/钉钉 |
| `workspace/AGENTS.md` | 新增 | 客服 Agent 身份 + 6 功能工作流 + 优先级指南 |
| `workspace/SOUL.md` | 修改 | CloudSync 智能客服人设：同理心、升级话术、闭环服务 |
| `workspace/USER.md` | 修改 | 单用户稳定画像：身份、偏好、沟通风格 |
| `workspace/skills/faq/SKILL.md` | 新增 | FAQ 知识库查询技能（always=true） |
| `workspace/skills/ticket/SKILL.md` | 新增 | 工单管理 + 问题升级 + 满意度评价（always=true） |
| `workspace/skills/memory/SKILL.md` | 新增 | 单用户记忆即时捕获（always=true，edit_file 精准编辑） |
| `workspace/knowledge_base/general.md` | 新增 | 通用 FAQ |
| `workspace/knowledge_base/billing.md` | 新增 | 计费 FAQ |
| `workspace/knowledge_base/api.md` | 新增 | API FAQ |
| `workspace/knowledge_base/troubleshooting.md` | 新增 | 排错 FAQ |
| `workspace/mcp_servers/ticket_server.py` | 新增 | 5 工具 MCP Server：JSON-RPC 2.0 over stdio + SQLite |
| `workspace/memory/MEMORY.md` | 新增 | 动态用户记忆（skill 即时写 + Dream 整理） |
| `nanobot/skills/memory/SKILL.md` | 修改 | builtin skill：允许手动编辑 MEMORY.md |
| `nanobot/templates/agent/dream_phase1.md` | 修改 | Dream 识别手动写入为权威来源 |
| `nanobot/templates/agent/dream_phase2.md` | 修改 | Phase 2 编辑前 re-read 最新内容 |
| `nanobot/templates/AGENTS.md` | 修改 | 移除 session key 解析用户 ID 的错误指令 |
| `nanobot/channels/dingtalk.py` | 修改 | 修复裸异常吞没 + 新增 send_delta 流式支持 |
| `nanobot/agent/memory.py` | 修改 | Dream Phase 2 前刷新 file_context |
| `nanobot/api/server.py` | 修改 | 注释修正：per-user → per-session |

**未创建的文件：** `message_router.py`（Flask 路由）— nanobot 框架原生处理多平台路由。`config.full.json`（已删除）— 冗余，代码无引用。

---

## 五、核心文件详解

### 5.1 SOUL.md — Bot 人设

```
workspace/SOUL.md
```

CloudSync 智能客服身份：
- **知识库优先** — 先查 FAQ，不编造
- **同理心** — 先认可感受再给方案
- **效率** — 一次性给全信息，关键步骤列表化
- **闭环** — 工单创建给工单号 + 预计时间，解决后确认满意度
- **升级场景** — 转人工/数据丢失/情绪激动/3 次复现 → 紧急工单 + 30 分钟 SLA

### 5.2 USER.md — 用户画像

```
workspace/USER.md
```

稳定信息（Dream 维护）：
- 身份：姓名、公司、角色
- 偏好：沟通风格、回复长度、技术水平
- 长期上下文：当前项目、常用平台

与 MEMORY.md 分工：USER.md 放不变的身份和偏好，MEMORY.md 放动态项目和近期问题。

### 5.3 AGENTS.md — Agent 行为定义

```
workspace/AGENTS.md
```

6 步工作流：
```
用户消息 → 读 MEMORY.md → 分类(FAQ/工单/升级) → 回复 → 满意度评价 → 记录记忆
```

### 5.4 config.json — 配置

```json
{
  "agents": { "defaults": {
    "model": "deepseek-chat", "provider": "deepseek",
    "unifiedSession": true, "timezone": "Asia/Shanghai"
  }},
  "channels": { "feishu": {...}, "dingtalk": {...}, "telegram": {"enabled": false} },
  "tools": { "mcpServers": { "ticket": {"command": "python", "args": [...]} } }
}
```

关键配置：
- `unifiedSession: true` — 飞书和钉钉共享会话和记忆
- `workspace` 使用相对路径 `"workspace"`，相对于执行目录解析
- Telegram 保持 `enabled: false`

### 5.5 ticket_server.py — 工单 MCP Server

```
workspace/mcp_servers/ticket_server.py
```

**协议**：JSON-RPC 2.0 over stdin/stdout  
**存储**：SQLite（`workspace/data/tickets.db`）  
**5 个工具**：

| 工具名 | 功能 |
|--------|------|
| `create_ticket` | 创建工单，支持 priority (low/medium/high/urgent) |
| `get_ticket` | 按 ID 查询工单详情 |
| `list_user_tickets` | 列出用户所有工单，支持 status 过滤 |
| `update_ticket` | 更新工单状态或添加评论 |
| `submit_feedback` | 记录满意度评分 (1-5) 和文字反馈 |

数据库 Schema：

```
ticket_id, title, description, priority, status, user_id,
user_name, platform, created_at, updated_at, comments(JSON),
satisfaction_rating(INTEGER 1-5), feedback_text
```

### 5.6 记忆系统：skill + Dream 互补

```
workspace/skills/memory/SKILL.md
```

| 层级 | 机制 | 作用 |
|------|------|------|
| 即时捕获 | skill `edit_file` 精准追加 MEMORY.md | 对话中关键信息立即落盘 |
| 定期整理 | Dream 每 2h 分析 history.jsonl | 去重、合并、发现可复用 skill |
| 冲突避免 | 两者都用 `edit_file`，不作全量覆写 | Dream Phase 2 前 re-read 最新内容 |

---

## 六、验证结果

### 6.1 独立测试

| 验证项 | 命令/方式 | 结果 |
|--------|----------|------|
| MCP Server 初始化 | `echo '{"jsonrpc":"2.0",...}' \| python ticket_server.py` | 5 tools registered |
| FAQ 查询 | `nanobot agent -m "How do I reset my password?"` | 搜索 knowledge_base/general.md，准确回答 |
| 工单创建 | `nanobot agent -m "I can't log in, create a ticket"` | 自动判定 high 优先级，工单持久化 |
| 工单查询 | `nanobot agent -m "Show me all my tickets"` | 列表展示 |

### 6.2 端到端测试（飞书）

| 测试场景 | 用户输入 | Bot 行为 | 结果 |
|---------|---------|---------|------|
| 问题升级 | "数据同步卡住了，转人工！" | 安抚 → urgent 工单 → SLA 30min → 飞书联系确认 | 通过 |
| 满意度评价 | "工单 TK-xxx 的问题解决了，谢谢" | 确认解决 → update_ticket → 要评分 → submit_feedback(5分) → 感谢 | 通过 |

### 6.3 Gateway 启动验证

```bash
python -m nanobot gateway -c workspace/config.json -v
```

输出确认：
```
✓ Channels enabled: dingtalk, feishu
✓ DingTalk Stream Mode WebSocket 已连接
✓ Feishu WebSocket 已连接 (bot: ou_97356235...)
✓ Dream: every 2h
✓ MCP ticket: 5 tools registered
```

---

## 七、启动方式

```bash
cd D:\Agent_Project\nanobot-main\nanobot-main
python -m nanobot gateway -c workspace/config.json -v
```

`workspace` 路径在 config.json 中已设置为相对路径 `"workspace"`，无需额外 `-w` 参数。

---

## 八、与文档教程的关键差异

| 维度 | 文档教程 | 本实施方案 |
|------|---------|-----------|
| 消息路由 | Flask message_router.py + Webhook | nanobot ChannelManager 原生处理 |
| 多平台连接 | 需要公网 IP + Nginx | WebSocket 长连接，无需公网 IP |
| 用户模型 | 多用户（假设） | 单用户 unified_session |
| MCP Server | 原始 JSON-RPC | 原始 JSON-RPC |
| 记忆系统 | MEMORY.md 概念 | skill 即时捕获 + Dream 定期整理 双轨 |
| 升级机制 | 无 | 5 触发条件 + SLA 4 级 + 话术模板 |
| 满意度 | 无 | submit_feedback + 1-5 评分 + 低分重开工单 |
| 部署 | 独立 Flask 服务 | `nanobot gateway` 单命令启动 |

核心原因：nanobot 是一个完整的 Agent 框架，已经内置了文档教程中需要手动构建的大部分基础设施。实施工作集中在 workspace 层的业务逻辑：身份定义、技能编写、知识库填充、MCP Server 开发、记忆策略设计。
