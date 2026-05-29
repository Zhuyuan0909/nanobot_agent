# RAG 设计中的问题与解决方案

## 问题总览

| # | 问题 | 严重程度 | 类型 |
|---|------|----------|------|
| 1 | HuggingFace 模型下载被墙 | 致命 | 环境/网络 |
| 2 | BM25 归一化人为抬高不相关查询分数 | 高 | 算法设计 |
| 3 | 小语料库下 embedding 相似度基线偏高 | 高 | 算法设计 |
| 4 | 中文跨语言检索分数偏低 | 中 | 模型特性 |
| 5 | MCP 子进程使用系统 Python 导致依赖缺失 | 中 | 环境/运维 |
| 6 | 模型首次加载超时 | 中 | 性能 |
| 7 | stdio 管道过早关闭导致服务器启动中断 | 低 | 测试方法 |
| 8 | Windows symlink 不支持导致 huggingface 缓存警告 | 低 | 环境兼容 |

---

## 问题 1：HuggingFace 模型下载被墙

### 现象

首次运行时，`sentence-transformers` 尝试从 `huggingface.co` 下载 `BAAI/bge-small-zh-v1.5` 模型，连接超时：

```
'[WinError 10060] 由于连接方在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败'
thrown while requesting HEAD https://huggingface.co/BAAI/bge-small-zh-v1.5/resolve/main/...
```

### 根因

`huggingface.co` 在中国大陆被 DNS 污染/阻断，无法直接访问。

### 解决方案

在导入 `sentence_transformers` 之前设置 HuggingFace 镜像环境变量：

```python
# 必须在 import sentence_transformers 之前设置
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import chromadb
from sentence_transformers import SentenceTransformer
```

`hf-mirror.com` 是 HuggingFace 的国内镜像站，模型下载速度和可用性均有保障。

### 经验

- 面向国内用户的 AI 应用，所有 HuggingFace 依赖都需要考虑镜像方案
- 环境变量必须在 `import` 之前设置，否则不会生效
- 首次下载后模型会缓存到 `~/.cache/huggingface/hub/`，后续启动无需联网

---

## 问题 2：BM25 归一化人为抬高不相关查询分数

### 现象

发送完全不相关的查询 "how to cook pasta"，Top-1 结果的 combined score 仍然高达 0.62：

```
Query: "how to cook pasta"
  #1 [medium] combined=0.6200  emb=0.4572  "How to delete my account?"
  #2 [medium] combined=0.6155  emb=0.4721  "How do I set up a webhook?"
```

按预期，不相关查询的所有结果分数应该低于 0.3。

### 根因

混合搜索算法中的 BM25 分数归一化方式有问题：

```python
bm25_scores = self.bm25.get_scores(tokenized_query)
bm25_max = bm25_scores.max()
bm25_norm = bm25_scores / bm25_max  # 归一化到 [0, 1]
```

BM25 归一化是**相对于当前批次最大值**的，而非绝对相关性。即使全部分数都很低，归一化后总会有一个 chunk 被标为 1.0。对于 "how to cook pasta"，由于 "how" 和 "to" 这两个停用词出现在大部分 chunk 中，BM25 对所有 chunk 都有非零分数，归一化后第一名的 BM25 分数接近 1.0。

加上 embedding 分数（0.45 左右），加权后 `0.3 * 1.0 + 0.7 * 0.45 = 0.62`，看起来像是一个中等相关的结果。

### 解决方案

放弃用 combined score 做质量判断，改用**原始 embedding 余弦相似度**——这是绝对值，不受归一化影响：

```python
# quality 基于 raw embedding score 判定（绝对值，0-1 之间有实际含义）
raw_emb = emb_scores[idx]
if raw_emb >= 0.6:
    quality = "high"      # 强相关，直接回答
elif raw_emb >= 0.4:
    quality = "medium"    # 部分相关，分享 + 建工单
else:
    quality = "low"       # 不相关，建工单
```

同时在顶层返回 `best_embedding_score` 和 `warning` 字段：

```python
best_emb_score = emb_scores[top_indices[0]]

if best_emb_score < 0.35:
    warning = "LOW_RELEVANCE: ...treat as 'no match'..."
elif best_emb_score < 0.5:
    warning = "PARTIAL_MATCH: ...share what you can, then create a ticket..."
```

修复后：

```
Query: "how to cook pasta"
  best_emb=0.4572
  warning=PARTIAL_MATCH: Results may not fully answer the question.
  #1 [medium] combined=0.6200  emb=0.4572  "How to delete my account?"
```

LLM 收到 `PARTIAL_MATCH` 警告后会分享有限信息同时创建工单，而不是假装能回答。

### 经验

- 归一化分数（BM25 norm、softmax 等）只适合做相对排序，不适合做绝对质量判断
- 必须保留一个**有物理含义的绝对值**（如余弦相似度）作为质量门槛
- RAG 系统的输出应该同时包含"排序分数"和"质量信号"，让 LLM 自行判断可信度

---

## 问题 3：小语料库下 embedding 相似度基线偏高

### 现象

即使是不相关查询，raw embedding 余弦相似度最低也在 0.4-0.45 范围内，远高于预期的 0.2。

### 根因

本项目知识库只有 28 个 chunk，且全部是同一领域的 FAQ 文档。在如此小的语料库中：
- 任何英文句子的 BGE embedding 向量与 FAQ 条目的余弦相似度都不会太低
- "how to cook pasta" 和 "How to delete my account?" 的相似度达到 0.46，因为两者共享 "how to + 动词 + 名词" 的句式结构
- BGE 模型的 embedding 空间中，同类句式天然有一定接近度

### 解决方案

这不是 bug，而是**小语料库的固有特性**。解决方案不是修改算法，而是：

1. **通过 quality 分级和 warning 系统给 LLM 提供上下文信号**（见问题 2 的解决方案）
2. **在 FAQ Skill 中定义基于分数的行为策略**：

```
Scores > 0.5  → 完全匹配，直接回答
Scores 0.3-0.5 → 部分匹配，分享内容 + 创建工单
Scores < 0.3  → 无匹配，立即创建工单
```

3. **对外解释时坦诚说明**：这是 embedding 检索在小语料库下的局限，生产环境中语料库增大后分数区分度会更明显

### 经验

- 小语料库的 RAG 不能只靠分数阈值判断是否命中，需要多层信号
- 面试时可以主动提及这个局限及应对策略，展示你对 RAG 的深度理解
- 语料库越大（数千到数万条），cosine similarity 的分数分布越接近正态，区分度越好

---

## 问题 4：中文跨语言检索分数偏低

### 现象

中文查询 "怎么注册账号？" 的 Top-1 结果正确（"How to register an account?"），但 raw embedding 分数只有 0.47：

```
Query: "怎么注册账号？"
  #1 [medium] combined=0.3279  emb=0.4685  "How to register an account?"
  warning=PARTIAL_MATCH
```

而英文查询 "how to register an account" 的分数是 0.87。

### 根因

知识库全部是英文内容，中文 query 与英文 document 之间是**跨语言映射**。BGE-small-zh-v1.5 虽然是中英双语模型，但跨语言语义对齐的精度天然低于同语言匹配。0.47 的跨语言相似度已经是一个不错的结果。

### 解决方案

1. **接受跨语言分数偏低的客观事实**——这是 embedding 模型的固有特性，不是 bug
2. **通过 warning 系统告知 LLM**：分数虽低但结果可能有价值（`PARTIAL_MATCH` → "分享内容 + 建工单"）
3. **长期方案**：如需要更好的跨语言效果，可以换用更大的 BGE 模型（`bge-base-zh-v1.5`、`bge-large-zh-v1.5`）或使用专门的中英对齐模型（如 `m3e-large`）

### 经验

- 跨语言 RAG 不能直接用同语言的分数阈值
- 结果的正确性比分数更重要——中文 query 的 Top-1 结果仍然正确
- 面试时可以用这个 case 解释"分数低不等于结果错"，展示对 embedding 空间的理解

---

## 问题 5：MCP 子进程使用系统 Python 导致依赖缺失

### 现象

测试 RAG 服务器时，子进程报错 `ModuleNotFoundError: No module named 'jieba'`。

### 根因

测试脚本中使用了 `python` 命令启动子进程：

```python
proc = subprocess.Popen(
    ['python', 'workspace/mcp_servers/rag_server.py'],  # 系统 Python
    ...
)
```

系统 Python 没有安装 `sentence-transformers`、`chromadb` 等依赖，这些包只安装在 venv 中。

### 解决方案

使用 venv 的 Python 执行文件路径：

```python
VENV_PYTHON = Path('venv/Scripts/python.exe')
proc = subprocess.Popen(
    [str(VENV_PYTHON), str(SERVER_PATH)],
    ...
)
```

对于生产环境（nanobot gateway 启动 MCP 服务器），`config.json` 中的 `"command": "python"` 会在 venv 激活后运行，使用的是 venv 中的 Python，所以不需要修改。

### 经验

- 测试脚本和非 venv 环境中启动子进程时，需要显式指定 venv 中的 Python 路径
- MCP 服务器的依赖管理是一个值得关注的运维问题——可以考虑用 Docker 统一环境

---

## 问题 6：模型首次加载超时

### 现象

首次测试时，`subprocess.communicate(timeout=120)` 在 120 秒内都没有收到服务器响应。

### 根因

首次加载 `sentence-transformers` + `BAAI/bge-small-zh-v1.5`：
- torch 初始化：~10 秒
- 模型下载（镜像）：~20 秒（24MB）
- tokenizer 加载 + 模型权重加载：~5 秒
- encoding 28 个 chunk：~3 秒
- 总计约 40-50 秒

加上子进程启动开销和 Windows 上的 I/O 延迟，可能超过预期等待时间。

### 解决方案

1. **使用 `proc.stderr.readline()` 轮询等待**，而非固定超时：

```python
while True:
    line = proc.stderr.readline()
    if 'RAG server ready' in line:
        break
```

2. **`config.json` 中 `toolTimeout` 设为 60 秒**（首次启动需要编码时间）
3. **chromadb 持久化缓存**：二次启动时跳过重索引，启动时间 < 2 秒

### 经验

- AI 模型加载的首次启动是一个需要关注的时间窗口
- stderr 日志是判断 MCP 服务器就绪状态的最可靠方式
- 持久化缓存可以大幅缩短后续启动时间

---

## 问题 7：stdio 管道过早关闭导致服务器启动中断

### 现象

使用 `echo '...' | python rag_server.py` 管道方式测试时，服务器在模型加载完成前 stdin 就被关闭，导致进程提前终止。

### 根因

Shell 管道的 `echo` 命令输出完数据后立即关闭管道写入端，子进程的 stdin 收到 EOF。此时如果模型还在加载中，`sys.stdin.readline()` 返回空字符串，`for line in sys.stdin` 循环结束，服务器退出。

### 解决方案

使用 `subprocess.Popen` + `communicate()` 方式：

```python
proc = subprocess.Popen(
    [python_path, server_path],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
# 先等待服务器就绪，再发送请求
# communicate() 会正确管理管道生命周期
```

### 经验

- MCP stdio 服务器的测试需要正确管理管道生命周期
- 不要用 shell 管道快捷方式测试需要长启动时间的进程

---

## 问题 8：Windows symlink 不支持导致 HuggingFace 缓存警告

### 现象

```
UserWarning: `huggingface_hub` cache-system uses symlinks by default
but your machine does not support them...
```

### 根因

Windows 默认不开启 symlink 支持（需要开发者模式或管理员权限）。

### 解决方案

非关键警告，文件仍然正确缓存。如需消除警告，可以设置环境变量：

```python
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
```

或者在 Windows 中开启开发者模式（设置 → 更新与安全 → 开发者选项）。

### 经验

- Windows 上部署 AI 工具链时，symlink 问题是常见的小摩擦
- 不影响功能，但日志噪声可能干扰真正的错误判断

---

## 设计决策反思

### 做得好的

1. **MCP 协议选型**：遵循项目已有的 `ticket_server.py` 模式，框架零改动，独立可测试
2. **混合搜索架构**：BM25 + Embedding 互补，错误码精确匹配和语义泛化两头兼顾
3. **质量信号设计**：从"归一化分数"改为"原始 embedding 绝对值"，解决了分数不可信的问题
4. **持久化缓存**：chromadb 本地存储，二次启动 < 2 秒

### 如果重新设计的改进点

1. **BM25 归一化**：应该在语料库构建时预计算 IDF 统计，用全局 IDF 而非批次内归一化
2. **加入 reranker**：在 Top-K 粗排后加一层 cross-encoder 精排，可以大幅提升不相关查询的拦截能力
3. **中文 KB**：应该有中文版本的知识库，让跨语言场景的分数自然提升
4. **监控埋点**：应该在服务器启动时就接入日志系统，记录每次查询的分数分布

---

## 面试可讲的"踩坑经验"

> "我在做 RAG 升级时遇到一个有意思的问题：BM25 归一化会人为抬高不相关查询的分数。因为归一化是相对于批次最大值的，即使查询完全不相关，总有一个 chunk 被标为 1.0。我后来的解决方案是用原始的 embedding 余弦相似度做质量判断——它是绝对值，有物理含义。0.4 的余弦相似度在所有语料库中含义基本一致，不受批次大小影响。"
>
> "另一个问题是小语料库的分数基线。只有 28 个 chunk 时，不相关查询的相似度也在 0.4-0.5。这不是 bug，是 dense retrieval 的固有特性——语料库越小，最近邻距离越近。我的处理方式是加了 quality 分级和 warning 系统，给 LLM 提供多层信号而不只靠分数判断。"
