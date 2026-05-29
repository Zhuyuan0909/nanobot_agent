FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir nanobot-ai sentence-transformers chromadb rank-bm25 jieba

ENV HF_ENDPOINT=https://hf-mirror.com
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

COPY workspace/ /app/workspace/

EXPOSE 18790
ENTRYPOINT ["nanobot"]
CMD ["gateway", "--config", "/app/workspace/config.json", "--workspace", "/app/workspace"]
