#!/usr/bin/env python3
"""RAG Knowledge Base MCP Server — JSON-RPC 2.0 over stdio.

Provides semantic search over the CloudSync FAQ knowledge base using
hybrid retrieval: BM25 keyword matching + BGE embedding similarity.

IMPORTANT: ALL debug/logging output MUST go to sys.stderr. Writing anything
other than JSON-RPC to stdout will break nanobot's MCP client connection.
"""

import json
import os
import re
import sys
from pathlib import Path

# Use HuggingFace mirror for users in China
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import jieba
import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# ---- paths ----

SERVER_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = SERVER_DIR.parent
KB_DIR = WORKSPACE_DIR / "knowledge_base"
DATA_DIR = WORKSPACE_DIR / "data" / "rag_cache"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def log(msg: str) -> None:
    print(f"[rag_server] {msg}", file=sys.stderr, flush=True)


# ---- tokenizer ----

def _tokenize(text: str) -> list[str]:
    """Tokenize with jieba (handles Chinese + English)."""
    return [t.strip() for t in jieba.cut(text.lower()) if t.strip()]


class RAGMCPServer:
    """RAG knowledge base MCP Server — speaks JSON-RPC 2.0 over stdin/stdout."""

    def __init__(self) -> None:
        self.chunks: list[dict] = []
        self.bm25: BM25Okapi | None = None
        self.model: SentenceTransformer | None = None
        self.collection: chromadb.Collection | None = None

        self._init_kb()

    # ------------------------------------------------------------------
    # KB loading, chunking, indexing
    # ------------------------------------------------------------------

    def _init_kb(self) -> None:
        """Load KB files, chunk, embed, index. Skip if cache is fresh."""
        log("Loading knowledge base...")
        self.chunks = self._load_and_chunk_kb(KB_DIR)
        log(f"  Chunked into {len(self.chunks)} sections from {len(set(c['metadata']['source'] for c in self.chunks))} files")

        log(f"Loading embedding model: {MODEL_NAME}")
        self.model = SentenceTransformer(MODEL_NAME)
        log("  Model ready")

        # BM25 index
        log("Building BM25 index...")
        self.bm25 = BM25Okapi([_tokenize(c["text"]) for c in self.chunks])
        log("  BM25 ready")

        # ChromaDB
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(DATA_DIR))
        self.collection = client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"},
        )

        if self.collection.count() == len(self.chunks):
            log(f"  ChromaDB cache hit ({self.collection.count()} vectors), skipping re-index")
        else:
            log(f"  ChromaDB cache miss (have {self.collection.count()}, need {len(self.chunks)}), re-indexing...")
            self._reindex_chromadb()

        log("RAG server ready.")

    def _load_and_chunk_kb(self, kb_dir: Path) -> list[dict]:
        """Parse all .md files, split by ## headings."""
        chunks = []
        for md_file in sorted(kb_dir.glob("*.md")):
            source = md_file.name
            topic = md_file.stem.replace("_", " ").title()
            content = md_file.read_text(encoding="utf-8")

            # Split by ## headings
            sections = re.split(r"\n(?=## )", content)
            for section in sections:
                # Extract heading from first line
                lines = section.strip().split("\n")
                first_line = lines[0].strip()
                if first_line.startswith("# "):
                    # This is the file title line — skip as a standalone chunk,
                    # but prepend it to the next real section
                    continue
                if first_line.startswith("## "):
                    heading = first_line[3:].strip()
                else:
                    heading = topic

                text = section.strip()
                if not text:
                    continue

                chunks.append({
                    "text": text,
                    "metadata": {
                        "source": source,
                        "topic": topic,
                        "heading": heading,
                    },
                })

        return chunks

    def _reindex_chromadb(self) -> None:
        """Delete existing collection data and re-embed all chunks."""
        # Delete all existing
        existing = self.collection.get()
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        texts = [c["text"] for c in self.chunks]
        metadatas = [c["metadata"] for c in self.chunks]
        ids = [str(i) for i in range(len(self.chunks))]

        log(f"  Encoding {len(texts)} chunks...")
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings.tolist(),
        )
        log(f"  Indexed {len(texts)} vectors")

    # ------------------------------------------------------------------
    # Hybrid search (Step 3 & 4)
    # ------------------------------------------------------------------

    def _hybrid_search(self, query: str, top_k: int = 5, alpha: float = 0.3) -> dict:
        """BM25 + embedding hybrid search with weighted merge."""
        # 1. BM25 keyword scores
        tokenized_query = _tokenize(query)
        bm25_scores = np.array(self.bm25.get_scores(tokenized_query))
        bm25_max = bm25_scores.max()
        if bm25_max > 0:
            bm25_norm = bm25_scores / bm25_max
        else:
            bm25_norm = bm25_scores  # all zeros

        # 2. Embedding similarity via ChromaDB
        query_embedding = self.model.encode([query], normalize_embeddings=True)[0]
        chroma_results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=len(self.chunks),
        )

        # Build embedding score map: chunk_idx -> similarity (1 - cosine_distance)
        emb_scores = np.zeros(len(self.chunks))
        for doc_id, distance in zip(chroma_results["ids"][0], chroma_results["distances"][0]):
            idx = int(doc_id)
            emb_scores[idx] = 1.0 - distance

        # 3. Weighted merge
        combined = alpha * bm25_norm + (1.0 - alpha) * emb_scores

        # 4. Rank and return top_k
        ranked_indices = np.argsort(combined)[::-1]
        top_indices = ranked_indices[:top_k]

        results = []
        for rank, idx in enumerate(top_indices, 1):
            c = self.chunks[idx]
            score = round(float(combined[idx]), 4)
            raw_emb = round(float(emb_scores[idx]), 4)
            if raw_emb >= 0.6:
                quality = "high"
            elif raw_emb >= 0.4:
                quality = "medium"
            else:
                quality = "low"
            results.append({
                "rank": rank,
                "score": score,
                "embedding_score": raw_emb,
                "quality": quality,
                "bm25_score": round(float(bm25_norm[idx]), 4),
                "source": c["metadata"]["source"],
                "topic": c["metadata"]["topic"],
                "heading": c["metadata"]["heading"],
                "text": c["text"],
            })

        best_score = round(float(combined[top_indices[0]]), 4)
        best_emb_score = round(float(emb_scores[top_indices[0]]), 4)

        # Use raw embedding similarity for relevance warning (absolute measure, not normalized)
        warning = None
        if best_emb_score < 0.35:
            warning = "LOW_RELEVANCE: No relevant results found. Best embedding similarity is below 0.35 — treat as 'no match' and create a ticket immediately."
        elif best_emb_score < 0.5:
            warning = "PARTIAL_MATCH: Results may not fully answer the question. Share what you can, then create a ticket."

        return {
            "query": query,
            "total_chunks": len(self.chunks),
            "best_score": best_score,
            "best_embedding_score": best_emb_score,
            "warning": warning,
            "results": results,
        }

    # ------------------------------------------------------------------
    # JSON-RPC dispatch
    # ------------------------------------------------------------------

    def handle_request(self, request: dict) -> dict | None:
        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": self._initialize()}
        if method.startswith("notifications/"):
            return None
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": self._list_tools()}
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": req_id, "result": self._call_tool(request.get("params", {}))}

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}

    def _initialize(self) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "rag-server", "version": "1.0.0"},
            "capabilities": {"tools": {}},
        }

    def _list_tools(self) -> dict:
        return {
            "tools": [
                {
                    "name": "search_knowledge_base",
                    "description": (
                        "Search the CloudSync knowledge base using AI-powered semantic retrieval. "
                        "Returns the most relevant FAQ entries for any product question. "
                        "Supports Chinese and English queries. Much more accurate than grep — "
                        "finds answers even when the user uses different words than the FAQ."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query — use the user's original question",
                            },
                            "top_k": {
                                "type": "integer",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 10,
                                "description": "Number of results to return (default: 5)",
                            },
                            "alpha": {
                                "type": "number",
                                "default": 0.3,
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": (
                                    "Keyword vs semantic weight: 0.0 = pure semantic, 1.0 = pure keyword. "
                                    "Default 0.3 (70% semantic) works well for most queries. "
                                    "Use 0.5 when searching for error codes or exact product names."
                                ),
                            },
                        },
                        "required": ["query"],
                    },
                }
            ]
        }

    def _call_tool(self, params: dict) -> dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name != "search_knowledge_base":
            return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}

        try:
            result = self._hybrid_search(
                query=arguments["query"],
                top_k=arguments.get("top_k", 5),
                alpha=arguments.get("alpha", 0.3),
            )
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        except Exception as exc:
            log(f"Search error: {exc}")
            return {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        log("Starting RAG MCP server...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                log(f"Invalid JSON received: {line[:100]}...")
            except KeyboardInterrupt:
                break
        log("Server stopped.")


if __name__ == "__main__":
    RAGMCPServer().run()
