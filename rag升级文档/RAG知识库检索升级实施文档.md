# RAG 知识库检索升级 — 实施文档

## 升级背景

### 升级前：grep 文本匹配

```
用户提问 → LLM 收到 FAQ Skill 指令 → 调用 nanobot 内置 GrepTool
         → Python re 正则逐行扫描 knowledge_base/*.md
         → LLM 人工判断匹配程度 → 直接回答 / 创建工单
```

**问题**：纯文本正则匹配，无语义理解。"怎么付钱"搜不到 "payment methods"，"数据过不去"搜不到 "sync failed"。

### 升级后：语义检索 + 关键词混合搜索

```
用户提问 → LLM 调用 mcp_rag_search_knowledge_base
         → RAG MCP Server 执行混合搜索
         → BM25(30%) + Embedding(70%) 加权排序
         → 返回 Top-K 结果（含 source/topic/heading/text/score）
         → LLM 根据分数判断匹配程度 → 直接回答 / 创建工单
```

---

## 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| Embedding 模型 | `BAAI/bge-small-zh-v1.5` (24MB) | 中英双语、MIT 协议、中文 NLP 社区主流 |
| 向量数据库 | `chromadb` (PersistentClient) | 轻量文件存储、工业界广泛使用、面试加分 |
| 关键词匹配 | `rank-bm25` + `jieba` 分词 | 精确匹配错误码和专有名词 |
| 混合权重 | 默认 alpha=0.3 (30% BM25 + 70% embedding) | 偏向语义但保留关键词精度 |
| 分块策略 | 按 Markdown `##` 标题切分 | KB 已是 Q&A 结构，自然分块保持完整性 |
| 传输协议 | MCP JSON-RPC 2.0 over stdio | 与项目已有 ticket_server.py 模式一致，框架零改动 |

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        nanobot Gateway                          │
│                                                                 │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────────────┐ │
│  │ Feishu   │   │ AgentLoop    │   │ ToolRegistry            │ │
│  │ Channel  │──▶│              │──▶│  ├── read_file (内置)    │ │
│  └──────────┘   │  System      │   │  ├── grep (内置)        │ │
│                 │  Prompt:     │   │  ├── mcp_ticket_* (MCP) │ │
│  ┌──────────┐   │  AGENTS.md   │   │  └── mcp_rag_* (MCP) ◀─┼─┼─── JSON-RPC over stdio
│  │ DingTalk │   │  SOUL.md     │   └─────────────────────────┘ │
│  │ Channel  │──▶│  USER.md     │                               │
│  └──────────┘   │  faq/SKILL.md│                               │
│                 │  ticket/     │                               │
│                 │  memory/     │                               │
│                 └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                                                                  │
                                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAG MCP Server (rag_server.py)               │
│                                                                 │
│  启动时：                                                        │
│    knowledge_base/*.md ──▶ 按 ## 标题分块 (28 chunks)            │
│                        ──▶ BGE embedding 编码                   │
│                        ──▶ chromadb 持久化 + BM25 索引           │
│                                                                 │
│  查询时：                                                        │
│    query ──▶ jieba 分词 → BM25 scores                           │
│          ──▶ BGE encode → chromadb query (余弦相似度)             │
│          ──▶ alpha * BM25 + (1-alpha) * Embedding               │
│          ──▶ 排序返回 Top-K                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 文件变更清单

### 新增文件

#### 1. `workspace/mcp_servers/rag_server.py`

RAG MCP 服务器主文件（237 行），遵循 `ticket_server.py` 的 JSON-RPC 2.0 over stdio 模式。

**类结构**：

```
RAGMCPServer
├── __init__()              # 加载 KB → 分块 → 初始化 BGE 模型 → 构建 BM25 → chromadb 索引
├── run()                   # stdin 读 JSON 行，stdout 写 JSON 行，stderr 打日志
├── handle_request()        # 按 method 字段分发到各 handler
├── _initialize()           # MCP 握手：返回协议版本和服务信息
├── _list_tools()           # 返回工具定义（JSON Schema）
├── _call_tool()            # 分发到 _hybrid_search()
│
├── _load_and_chunk_kb()    # 解析 knowledge_base/*.md，按 ## 标题切分（28 chunks）
├── _init_kb()              # 总控：加载分块 → 初始化模型 → BM25 → chromadb
├── _reindex_chromadb()     # 全量重建 chromadb 索引
└── _hybrid_search()        # BM25 + embedding 混合搜索，加权排序返回 Top-K
```

**关键实现细节**：

- HuggingFace 国内镜像：`os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"`（解决 huggingface.co 被墙问题）
- chromadb 缓存检测：`collection.count() == len(chunks)` → 跳过重索引
- 混合权重默认 `alpha=0.3`：30% BM25（关键词精度）+ 70% Embedding（语义泛化）
- 错误码查询建议 `alpha=0.5`

#### 2. `workspace/mcp_servers/test_rag.py`

自动化测试脚本，包含 8 个测试用例，覆盖：
- 英文语义查询
- 中文跨语言查询
- 精确错误码查询
- 同义改写查询
- chromadb 缓存持久化验证

#### 3. `workspace/data/rag_cache/`（自动创建）

chromadb 持久化目录，存储 28 个 512 维 BGE embedding 向量。二次启动时检测缓存命中，跳过重索引（启动 < 1 秒）。

### 修改文件

#### 4. `workspace/config.json`

在 `tools.mcpServers` 下新增 RAG 服务器配置：

```json
"rag": {
  "command": "python",
  "args": ["workspace/mcp_servers/rag_server.py"],
  "toolTimeout": 60
}
```

#### 5. `workspace/skills/faq/SKILL.md`

**核心变更**：将 Query Workflow Step 2 从 grep + read_file 替换为 MCP 工具调用。

| 项目 | 升级前 | 升级后 |
|------|--------|--------|
| 搜索方式 | `grep -i "keyword" knowledge_base/xxx.md` | `mcp_rag_search_knowledge_base(query="...", top_k=5, alpha=0.3)` |
| 结果质量 | 正则匹配行 | 语义排序 Top-K（含分数、来源、标题、全文） |
| 中文支持 | 无（关键词对不上就搜不到） | 跨语言语义匹配 |
| 判断依据 | LLM 人工读文件判断 | 分数阈值：>0.5 完全匹配，0.3-0.5 部分匹配，<0.3 无匹配 |

---

## 依赖安装

```bash
pip install sentence-transformers chromadb rank-bm25 jieba
```

| 包 | 用途 | 大小 |
|---|---|---|
| `sentence-transformers` | BGE embedding 模型加载和推理 | ~200MB（含 torch） |
| `chromadb` | 向量存储和余弦相似度查询 | ~50MB |
| `rank-bm25` | BM25 关键词匹配算法 | <1MB |
| `jieba` | 中文分词（BM25 用） | ~5MB |

---

## 检索质量测试结果

### 测试环境

- Windows 10, Python 3.13
- Embedding 模型：BAAI/bge-small-zh-v1.5
- 知识库：4 个 Markdown 文件，28 个 chunk

### 测试结果（8/8 通过）

| # | 查询 | 期望文件 | 命中结果 | 分数 | 结果 |
|---|---|---|---|---|---|
| 1 | "How do I reset my password?" | general.md | How to reset my password? | 0.8422 | PASS |
| 2 | "I want to pay with Alipay" | billing.md | What payment methods are accepted? | 0.7509 | PASS |
| 3 | "I keep getting error 429" | api.md | Common API error codes | 0.8337 | PASS |
| 4 | "My dashboard is slow" | troubleshooting.md | Why is my dashboard loading slowly? | 0.7532 | PASS |
| 5 | "怎么注册账号？" (中文) | general.md | How to register an account? | 0.3279 | PASS |
| 6 | "CS-ERR-5001" (错误码) | troubleshooting.md | Error message: CS-ERR-5001... | 0.7986 | PASS |
| 7 | "what payment methods are accepted?" | billing.md | What payment methods are accepted? | 0.8711 | PASS |
| 8 | "how to get an API key?" | api.md | How do I get an API key? | 0.8741 | PASS |

### 关键发现

1. **英文语义检索**：Top-1 正确率 100%，平均分数 0.82
2. **中文跨语言检索**：正确但分数偏低（0.33），因为 KB 是英文、query 是中文，BGE 做跨语言匹配。结果正确，LLM 可根据低分判断为 "partial match" 并创建工单
3. **精确错误码**：alpha=0.5 时 BM25 权重更高，CS-ERR-5001 精确命中
4. **缓存持久化**：二次启动显示 "ChromaDB cache hit (28 vectors), skipping re-index"，启动 < 1 秒

---

## 面试可讲要点

### 为什么做这个升级

> "原来的知识库检索是 grep 正则匹配，没有任何语义理解能力。用户说'怎么付钱'搜不到 'payment methods'，说'数据过不去'搜不到 'sync failed'。我把检索升级为混合搜索方案——BM25 做关键词精确匹配 + BGE embedding 做语义检索，用 chromadb 做向量存储。"

### 技术选型理由

> "Embedding 模型选 BGE-small-zh-v1.5，因为它中英双语、24MB 轻量、MIT 协议。向量数据库选 chromadb，因为它是文件级持久化、不需要额外服务进程，适合嵌入到 MCP server 里。混合权重默认 0.3 偏语义，但查询错误码时调到 0.5 偏关键词——这样'CS-ERR-5001'能精确命中。"

### 架构设计理由

> "遵循项目已有的 MCP 协议模式，把 RAG 做成了独立的 JSON-RPC 服务器，通过 stdio 与 nanobot 通信。这样 RAG 的依赖（torch、chromadb）和主框架完全解耦，可以独立测试、独立部署。"

### 分块策略

> "知识库本身就是 Q&A 结构，每个 ## 标题下是一个独立的 FAQ 条目。我按 Markdown 标题切分而不是固定窗口大小，这样每个 chunk 都是完整的问答单元，保留了语义完整性。4 个文件切出 28 个 chunk。"

### 混合搜索算法

> "BM25 负责精确匹配——错误码、API 名称、专有名词。Embedding 负责语义泛化——同义词、跨语言、改写。两个分数归一化后用加权平均合并，alpha 控制偏重。这个参数也对 LLM 暴露，LLM 可以根据查询类型自行调整。"
