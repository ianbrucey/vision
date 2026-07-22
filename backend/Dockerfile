FROM python:3.13-slim

# postgresql-client: init_db wait-loop uses pg_isready.
# curl/gnupg/ca-certificates: needed to install the Node.js apt repo below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js — required because claude_agent_sdk (backend/requirements.txt)
# shells out to the claude CLI binary at runtime. The CLI reads
# ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN from the environment, which in
# this project point at the DeepSeek Anthropic-compatible endpoint
# (see .env.prod ANTHROPIC_* vars).
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

RUN useradd --create-home --shell /bin/bash vision && chown -R vision:vision /app
USER vision

EXPOSE 8400

ENTRYPOINT ["./docker-entrypoint.sh"]
