# 📚 Nanobot 项目学习路线图

这是一个**AI Agent 框架**项目，用于构建能够使用工具、与多个聊天平台集成的智能助手。作为刚学完 Python 基础的学生，这是一个很好的进阶项目。以下是你需要学习的知识体系：

## 第一阶段：Python 进阶基础（1-2 周）

在深入项目前，你需要掌握这些 Python 特性：

### 1. 异步编程（Async/Await）⭐⭐⭐⭐⭐

- 这个项目大量使用 `async/await`，特别是在 `runner.py`、`loop.py` 中
- 学习：`asyncio` 库、事件循环、协程、任务管理
- 为什么重要：Agent 需要并发处理多个工具调用和消息

**学习重点**：
- `async def` 和 `await` 关键字
- `asyncio.create_task()` 和 `asyncio.gather()`
- 异常处理和超时管理

### 2. 类型提示（Type Hints）⭐⭐⭐⭐

- 项目使用了完整的类型注解（`from typing import ...`）
- 学习：`typing` 模块、泛型、`dataclass`、类型检查
- 为什么重要：理解函数签名和数据结构

**学习重点**：
- 基本类型注解：`str`, `int`, `list[str]`, `dict[str, Any]`
- 泛型：`Generic`, `TypeVar`
- 联合类型：`Union`, `Optional`

### 3. 装饰器和元编程⭐⭐⭐

- 项目中有 hooks、装饰器模式
- 学习：函数装饰器、类装饰器、`functools`

**学习重点**：
- 函数装饰器的原理
- `@wraps` 装饰器
- 类装饰器

### 4. 数据类（Dataclass）⭐⭐⭐⭐

- 项目大量使用 `@dataclass` 定义数据结构
- 学习：`dataclasses` 模块、`slots` 优化

**学习重点**：
- `@dataclass` 装饰器
- `field()` 函数和默认值
- `slots=True` 性能优化

---

## 第二阶段：核心概念理解（2-3 周）

### 1. Agent 架构基础⭐⭐⭐⭐⭐

**学习顺序**：
1. `nanobot/nanobot.py` — 公共 API 入口
2. `nanobot/agent/runner.py` — Agent 执行循环的核心
3. `nanobot/agent/loop.py` — 高级循环管理

**关键概念**：
- **Agent 循环**：接收消息 → 调用 LLM → 执行工具 → 返回结果 → 重复
- **工具调用（Tool Calling）**：LLM 决定使用哪个工具，Agent 执行它
- **消息历史管理**：维护对话上下文
- **上下文窗口管理**：处理 token 限制

**核心流程**：
```
用户消息
    ↓
Agent 循环
    ↓
调用 LLM（带工具定义）
    ↓
LLM 返回工具调用请求
    ↓
执行工具
    ↓
将结果返回给 LLM
    ↓
LLM 生成最终响应
    ↓
返回给用户
```

### 2. 工具系统（Tool System）⭐⭐⭐⭐⭐

**学习顺序**：
1. `nanobot/agent/tools/base.py` — 工具基类
2. `nanobot/agent/tools/registry.py` — 工具注册表
3. `nanobot/agent/tools/shell.py` — 具体工具实现示例
4. `nanobot/agent/tools/filesystem.py` — 文件系统工具

**关键概念**：
- **工具定义**：每个工具有名称、描述、参数
- **工具执行**：安全地执行用户请求的操作
- **工具结果处理**：将结果返回给 Agent
- **工具注册**：动态注册和发现工具

**工具的三个关键部分**：
1. 元数据（名称、描述、参数定义）
2. 执行函数（实际执行逻辑）
3. 结果处理（格式化返回结果）

### 3. LLM 提供者（Providers）⭐⭐⭐⭐

**学习顺序**：
1. `nanobot/providers/base.py` — 提供者基类
2. `nanobot/providers/anthropic_provider.py` — Anthropic 实现
3. `nanobot/providers/openai_compat_provider.py` — OpenAI 兼容实现
4. `nanobot/providers/registry.py` — 提供者注册表

**关键概念**：
- **统一接口**：不同 LLM 的统一接口（OpenAI、Anthropic、Azure 等）
- **模型调用**：发送消息和工具定义到 LLM
- **响应处理**：解析 LLM 的响应
- **Token 管理**：估算和管理 token 使用
- **错误处理和重试**：处理 API 失败

**支持的提供者**：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- 本地模型 (Ollama, vLLM)
- 其他兼容 OpenAI 的服务

### 4. 配置系统⭐⭐⭐

**学习顺序**：
1. `nanobot/config/schema.py` — 配置结构定义
2. `nanobot/config/loader.py` — 配置加载
3. `nanobot/config/paths.py` — 路径管理

**关键概念**：
- **配置文件格式**：JSON 配置
- **环境变量支持**：从环境变量覆盖配置
- **默认值**：合理的默认配置
- **验证**：配置验证和错误提示

---

## 第三阶段：高级特性（2-3 周）

### 1. 内存系统（Memory）⭐⭐⭐⭐

**文件**：`nanobot/agent/memory.py`

**关键概念**：
- **对话历史存储**：持久化保存对话
- **内存检索**：快速查找相关历史
- **内存压缩**：总结旧对话以节省 token
- **多会话管理**：隔离不同用户的对话

**学习重点**：
- 如何存储和检索消息
- 内存的生命周期管理
- 与 Agent 循环的集成

### 2. 消息总结（Context Compaction）⭐⭐⭐

**文件**：`nanobot/agent/autocompact.py`

**关键概念**：
- **上下文窗口限制**：LLM 有 token 限制
- **自动压缩**：当接近限制时自动总结
- **选择性保留**：保留最近的消息，总结旧消息
- **质量保证**：确保总结不丢失重要信息

**学习重点**：
- Token 估算算法
- 压缩策略
- 何时触发压缩

### 3. 多渠道集成⭐⭐⭐

**文件夹**：`nanobot/channels/`

**支持的渠道**：
- Slack
- Discord
- Telegram
- Feishu（飞书）
- WeChat（微信）
- Email
- WebSocket
- 等等

**关键概念**：
- **渠道适配器**：将不同平台的消息转换为统一格式
- **消息格式转换**：处理富文本、图片、文件等
- **认证和连接**：管理与各平台的连接
- **事件处理**：处理来自各平台的事件

**学习重点**：
- 渠道基类的设计
- 如何实现新渠道
- 消息格式的转换

### 4. MCP（Model Context Protocol）⭐⭐⭐

**文件**：`nanobot/agent/tools/mcp.py`

**关键概念**：
- **标准化工具接口**：MCP 定义了工具的标准格式
- **资源访问**：通过 MCP 访问外部资源
- **提示词注入**：MCP 可以提供系统提示词
- **服务器集成**：连接到 MCP 服务器

**学习重点**：
- MCP 协议基础
- 如何集成 MCP 服务器
- 资源和工具的区别

### 5. 事件系统和 Hooks⭐⭐⭐

**文件**：
- `nanobot/agent/hook.py` — Hook 定义
- `nanobot/bus/events.py` — 事件定义
- `nanobot/bus/queue.py` — 事件队列

**关键概念**：
- **生命周期事件**：Agent 执行的各个阶段
- **Hook 机制**：在特定事件处执行自定义代码
- **事件总线**：发布-订阅模式
- **扩展点**：允许用户自定义行为

**关键事件**：
- `on_message_received` — 收到消息
- `on_tool_call` — 调用工具
- `on_tool_result` — 工具返回结果
- `on_response_generated` — 生成响应
- `on_error` — 发生错误

---

## 第四阶段：实战项目（2-4 周）

### 项目 1：简单工具扩展

**目标**：在 `tools/` 中添加一个新工具

**步骤**：
1. 创建新文件 `nanobot/agent/tools/weather.py`
2. 继承 `BaseTool` 类
3. 实现 `execute()` 方法
4. 在 `tools/registry.py` 中注册
5. 测试工具的调用

**学习收获**：
- 工具的完整生命周期
- 如何定义工具参数
- 错误处理

### 项目 2：自定义 Agent

**目标**：基于 Nanobot 框架创建一个特定领域的 Agent

**示例**：
- 代码审查 Agent
- 文档生成 Agent
- 数据分析 Agent

**步骤**：
1. 定义 Agent 的专业领域和能力
2. 选择合适的工具组合
3. 编写系统提示词
4. 测试和优化

**学习收获**：
- 如何组合工具
- 提示词工程
- Agent 的实际应用

### 项目 3：新渠道集成

**目标**：实现一个新的聊天渠道

**步骤**：
1. 选择一个平台（如钉钉、企业微信）
2. 继承 `BaseChannel` 类
3. 实现消息接收和发送
4. 处理认证和连接
5. 测试集成

**学习收获**：
- 渠道适配的模式
- 异步编程实践
- API 集成

### 项目 4：内存和上下文优化

**目标**：实现自定义的内存策略

**步骤**：
1. 分析当前内存系统
2. 设计新的内存策略
3. 实现自定义内存类
4. 测试和性能评估

**学习收获**：
- 内存管理的复杂性
- 性能优化
- 权衡设计

---

## 学习资源推荐

| 主题 | 资源 | 难度 |
|------|------|------|
| 异步编程 | Real Python 的 Async IO 教程 | ⭐⭐⭐ |
| 类型提示 | Python 官方文档 typing 模块 | ⭐⭐ |
| LLM 工具调用 | OpenAI Function Calling 文档 | ⭐⭐⭐ |
| Agent 架构 | ReAct 论文、LangChain 文档 | ⭐⭐⭐⭐ |
| 项目代码 | 从 `runner.py` 开始，逐步深入 | ⭐⭐⭐⭐ |
| 设计模式 | 《Python 设计模式》 | ⭐⭐⭐ |

---

## 学习建议

### 1. 不要一次性读完所有代码
- 按照上面的阶段逐步深入
- 每个阶段花 1-2 周时间
- 完成实战项目后再进入下一阶段

### 2. 边学边实践
- 修改代码、添加日志、运行测试
- 在 IDE 中设置断点调试
- 尝试改变参数看效果

### 3. 理解"为什么"
- 不只是读代码，要理解设计决策
- 思考为什么这样设计而不是那样
- 查看 Git 历史了解演变过程

### 4. 从简单到复杂
- 先理解 Agent 循环的基本流程
- 再学习工具系统
- 最后学习高级特性

### 5. 查看测试代码
- 测试文件通常展示了如何使用 API
- 从测试反推功能的使用方式
- 运行测试验证理解

### 6. 阅读文档和注释
- 查看 `README.md` 和 `docs/` 文件夹
- 阅读代码中的 docstring
- 理解每个模块的职责

### 7. 参与社区
- 查看 GitHub Issues 了解常见问题
- 阅读 Pull Requests 学习改进方式
- 在讨论中提出问题

---

## 关键文件导航

### 核心文件
```
nanobot/
├── nanobot.py                 # 公共 API 入口
├── agent/
│   ├── runner.py              # Agent 执行循环核心
│   ├── loop.py                # 高级循环管理
│   ├── memory.py              # 内存系统
│   ├── hook.py                # Hook 机制
│   ├── autocompact.py         # 上下文压缩
│   └── tools/
│       ├── base.py            # 工具基类
│       ├── registry.py        # 工具注册表
│       ├── shell.py           # Shell 工具
│       ├── filesystem.py      # 文件系统工具
│       └── mcp.py             # MCP 工具
├── providers/
│   ├── base.py                # 提供者基类
│   ├── anthropic_provider.py  # Anthropic 实现
│   ├── openai_compat_provider.py  # OpenAI 兼容
│   └── registry.py            # 提供者注册表
├── channels/                  # 多渠道集成
│   ├── base.py                # 渠道基类
│   ├── slack.py               # Slack 渠道
│   ├── discord.py             # Discord 渠道
│   └── ...
├── config/
│   ├── schema.py              # 配置结构
│   ├── loader.py              # 配置加载
│   └── paths.py               # 路径管理
└── bus/
    ├── events.py              # 事件定义
    └── queue.py               # 事件队列
```

---

## 学习进度检查清单

### 第一阶段完成标志
- [ ] 能够编写基本的 async/await 代码
- [ ] 理解类型提示的用途和语法
- [ ] 能够使用装饰器
- [ ] 理解 dataclass 的优势

### 第二阶段完成标志
- [ ] 能够解释 Agent 循环的完整流程
- [ ] 理解工具系统的设计
- [ ] 能够添加新工具
- [ ] 理解不同 LLM 提供者的区别

### 第三阶段完成标志
- [ ] 理解内存系统的工作原理
- [ ] 能够解释上下文压缩的必要性
- [ ] 理解渠道适配的模式
- [ ] 了解 MCP 的基本概念

### 第四阶段完成标志
- [ ] 完成至少 2 个实战项目
- [ ] 能够独立添加新功能
- [ ] 理解项目的整体架构
- [ ] 能够解释设计决策

---

## 常见问题

### Q: 我应该从哪个文件开始读？
A: 从 `nanobot/nanobot.py` 开始，这是公共 API 入口，能快速了解项目的使用方式。然后深入 `agent/runner.py` 理解核心循环。

### Q: 为什么项目使用这么多异步代码？
A: 因为 Agent 需要并发处理多个工具调用、网络请求等，异步编程能提高效率和响应速度。

### Q: 我可以跳过某些阶段吗？
A: 不建议。每个阶段都为下一个阶段奠定基础。如果某个概念不清楚，会影响后续学习。

### Q: 学完这个项目能做什么？
A: 你可以：
- 构建自己的 AI Agent
- 为 Nanobot 贡献代码
- 理解 LLM 应用的架构
- 在工作中应用这些知识

### Q: 需要多长时间完成全部学习？
A: 根据你的学习速度和投入时间，通常需要 2-3 个月。如果每周投入 10-15 小时，可以在 1-2 个月内完成。

---

## 下一步行动

1. **立即开始**：选择第一阶段的一个主题，花 1 周时间深入学习
2. **建立学习环境**：克隆项目，安装依赖，运行示例
3. **记录笔记**：在学习过程中记录关键概念和疑问
4. **实践编码**：不要只读代码，要动手修改和测试
5. **寻求帮助**：遇到问题时查看文档、GitHub Issues 或社区讨论

祝你学习顺利！🚀
