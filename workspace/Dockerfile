FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir nanobot-ai

COPY workspace/ /app/workspace/

RUN mkdir -p /app/workspace/data && \
    useradd -m -u 1000 -s /bin/bash nanobot && \
    chown -R nanobot:nanobot /app

USER nanobot

EXPOSE 18790

ENTRYPOINT ["nanobot"]
CMD ["gateway", "--config", "/app/workspace/config.json", "--workspace", "/app/workspace"]
