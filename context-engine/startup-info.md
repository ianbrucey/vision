# Vision — Startup & Infrastructure Guide

> **Audience:** Developer bringing Vision online on a new machine.
> **Assumes:** macOS or Linux with Docker, Python 3.14+, Node.js 22+, and `psql` client available.

---

## 1. Architecture at a Glance

```
┌─────────────────────────────────────────────┐
│                 YOUR MACHINE                  │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Next.js   │  │ FastAPI   │  │ Ingestion│  │
│  │ :3000     │  │ :8400     │  │ Worker   │  │
│  │ (dev)     │  │ (REST+SSE)│  │ (bg job) │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        │              │              │        │
│        └──────────────┼──────────────┘        │
│                       │                       │
│              ┌────────▼────────┐              │
│              │   PostgreSQL 15 │              │
│              │   + pgvector    │              │
│              │   :5433         │              │
│              └─────────────────┘              │
│                       │                       │
│              ┌────────▼────────┐              │
│              │   MinIO (S3)    │              │
│              │   :9002/:9003   │              │
│              └─────────────────┘              │
└─────────────────────────────────────────────┘
```

Three processes, two persistent services. The API auto-bootstraps the database on first startup. The ingestion worker polls for new jobs. The frontend dev server proxies to the API.

---

## 2. Prerequisites

| Dependency | Version | Check |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 22+ | `node --version` |
| npm | 10+ | `npm --version` |
| psql | 15+ | `psql --version` |
| PostgreSQL | 15+ with pgvector | See §3 (DBngin or Docker) |
| MinIO | Any recent | See §3 (DBngin or Docker) |

**One-time setup:**
```bash
./setup.sh
```
Or manually:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

---

## 3. Infrastructure Services

Two options: **DBngin** (macOS GUI — zero config) or **Docker Compose** (cross-platform).

### Option A: DBngin (macOS)

DBngin is a native macOS app that manages PostgreSQL and MinIO with a menu bar UI.
Download from [dbngin.com](https://dbngin.com).

| Service | Port | Credentials |
|---|---|---|
| PostgreSQL 15+ with pgvector | `5432` | System user (no password) |
| MinIO | `9000` (S3 API) | `minioadmin` / `minioadmin` |

Create the database and bucket:
```bash
createdb -h 127.0.0.1 -p 5432 -U "$(whoami)" vision
```
The MinIO `vision-uploads` bucket is created automatically by `./setup.sh` or on first upload.

`.env` for DBngin:
```
VISION_DB_HOST=127.0.0.1
VISION_DB_PORT=5432
VISION_DB_USERNAME=<your macOS username>
VISION_DB_PASSWORD=
MINIO_ENDPOINT=127.0.0.1:9000
```

### Option B: Docker Compose

Two services defined in [docker-compose.yml](../docker-compose.yml):

| Service | Image | Port | Credentials |
|---|---|---|---|
| `vision-db` | `pgvector/pgvector:pg15` | `5433` (host) → `5432` (container) | `vision` / `vision_dev` |
| `vision-minio` | `minio/minio:latest` | `9002` (S3 API), `9003` (console) | `minioadmin` / `minioadmin` |
| `vision-minio-init` | `minio/mc:latest` | — (one-shot) | Creates `vision-uploads` bucket |

**Why port 5433?** Coexists with a homebrew PostgreSQL on 5432 without conflict.

```bash
# Start both services
docker compose -f docker-compose.yml up -d

# Verify
docker compose -f docker-compose.yml ps
PGPASSWORD=vision_dev psql -h 127.0.0.1 -p 5433 -U vision -d vision -c "SELECT 1"
curl -s http://127.0.0.1:9002/minio/health/live
```

`.env` for Docker:
```
VISION_DB_HOST=127.0.0.1
VISION_DB_PORT=5433
VISION_DB_USERNAME=vision
VISION_DB_PASSWORD=vision_dev
MINIO_ENDPOINT=127.0.0.1:9002
```

---

## 4. Environment Variables

Copy and edit the template:
```bash
cp .env.example .env
```
`.env.example` is provided in the repo root with defaults for both DBngin and Docker.

All variables and their purposes:

### Database
| Variable | Default | Purpose |
|---|---|---|
| `VISION_DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `VISION_DB_PORT` | `5433` | Must match `docker-compose.yml` port mapping |
| `VISION_DB_DATABASE` | `vision` | Database name |
| `VISION_DB_USERNAME` | `vision` | Database role |
| `VISION_DB_PASSWORD` | `vision_dev` | Database password |

### LLM / AI
| Variable | Purpose |
|---|---|
| `ANTHROPIC_BASE_URL` | API base URL (e.g., `https://api.deepseek.com/anthropic` for DeepSeek) |
| `ANTHROPIC_AUTH_TOKEN` | API key for the LLM provider (also accepts `ANTHROPIC_API_KEY`) |
| `ANTHROPIC_MODEL` | Model ID (e.g., `deepseek-v4-pro`, `claude-sonnet-4-6`) |
| `MISTRAL_API_KEY` | Mistral API key (for embeddings) |
| `DATALAB_API_KEY` | DataLab API key (for OCR — optional) |

### Storage
| Variable | Default | Purpose |
|---|---|---|
| `MINIO_ENDPOINT` | `127.0.0.1:9002` | MinIO S3 endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `vision-uploads` | Bucket for uploaded documents |
| `MINIO_SECURE` | `false` | Set to `true` for TLS |

### JWT
| Variable | Default | Purpose |
|---|---|---|
| `VISION_JWT_SECRET` | `vision-dev-secret-change-in-production` | HMAC secret for JWT tokens |

**Important:** The `.env` file is loaded by `_load_dotenv()` in `core/db.py`. It runs at import time, before any connections are made. Environment variables already set in the shell take precedence over `.env` values.

---

## 5. Database Schema

### Schema Files (numbered, applied in order)

| File | Version | Tables Created | Size |
|---|---|---|---|
| [001_core.sql](../backend/schemas/001_core.sql) | v1 | `cases`, `parties`, `allegations`, `documents`, `sections`, `blocks`, `block_headings`, `citations`, `events`, `workspaces`, `embedding_cache`, `users`, `schema_migrations`, `jobs` (14) | 444 lines |
| [002_strategy.sql](../backend/schemas/002_strategy.sql) | v2 | `rhetorical_moves`, `case_facts`, `strategies`, `doctrine_elements`, `strategy_propositions`, `strategy_facts`, `proposition_fact_mappings`, `proposition_authorities`, `adversarial_attacks`, `adversarial_turns`, `proposition_overlay_gates`, `gauntlet_check_categories`, `gauntlet_check_definitions`, `strategy_gauntlet_results` (14) | 760 lines |
| [003_chat.sql](../backend/schemas/003_chat.sql) | v3 | `session_store_entries`, `chat_sessions`, `chat_messages` (3) | 119 lines |

**Total: 31 tables across the `vision` schema.**

### Required PostgreSQL Extensions

| Extension | Purpose |
|---|---|
| `vector` | 1024-dimensional embeddings for semantic search (Mistral embed) |
| `pg_trgm` | Trigram fuzzy matching on section titles and text search |

Both are included in the `pgvector/pgvector:pg15` Docker image.

### Schema Application

**Option A — Dedicated init script (recommended for new machines):**
```bash
cd backend && source ../.venv/bin/activate && python init_db.py
```
Outputs a table-by-table verification with pass/fail for each extension and schema file. Safe to run repeatedly.

**Option B — Automatic on API startup:**
The API applies all three schemas via a FastAPI `startup` event handler. No manual step needed — just start the API. The schemas use `IF NOT EXISTS` everywhere, so it's idempotent across restarts.

### Schema Verification

```bash
PGPASSWORD=vision_dev psql -h 127.0.0.1 -p 5433 -U vision -d vision -c "
SELECT version, name, applied_at FROM vision.schema_migrations ORDER BY version;
"

PGPASSWORD=vision_dev psql -h 127.0.0.1 -p 5433 -U vision -d vision -c "
SELECT count(*) AS table_count FROM pg_tables WHERE schemaname = 'vision';
"
# Expected: 31
```

---

## 6. Starting the Application

### The `start.sh` Script (all-in-one)

```bash
cd scripts/vision
chmod +x start.sh
./start.sh
```

This launches, in order:
1. MinIO (via docker compose, if not already running)
2. API server — `uvicorn api.main:app` on `:8400`
3. Ingestion worker — polls for document processing jobs
4. Frontend — `npm run dev` on `:3000`

Press `Ctrl+C` to stop all services. The script traps SIGINT and cleans up.

### Manual Start (individual services)

```bash
# Terminal 1 — API
cd scripts/vision/backend
source ../.venv/bin/activate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8400 --reload

# Terminal 2 — Ingestion worker
cd scripts/vision/backend
source ../.venv/bin/activate
python ingestion/worker.py

# Terminal 3 — Frontend
cd scripts/vision/frontend
npm run dev -- -p 3000
```

### Health Verification

```bash
# API health
curl http://127.0.0.1:8400/api/health
# → {"status":"ok","version":"0.1.0"}

# Auth test
curl -X POST http://127.0.0.1:8400/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123456"}'
# → {"user":{...},"token":"eyJ..."}

# Chat streaming test (requires a case to exist)
cd backend && source ../.venv/bin/activate
python tests/test_chat_stream.py

# Frontend
curl http://127.0.0.1:3000
# → HTML (Next.js dev server)

# API docs (FastAPI Swagger)
open http://127.0.0.1:8400/docs
```

---

## 7. Port Map

| Port | Service | External? |
|---|---|---|
| `3000` | Next.js frontend dev server | Yes — browser |
| `8400` | FastAPI backend | Yes — browser, frontend proxy |
| `5432` | PostgreSQL (DBngin) | Internal |
| `5433` | PostgreSQL (Docker) | Internal |
| `9000` | MinIO S3 API (DBngin) | Internal |
| `9002` | MinIO S3 API (Docker) | Internal |
| `9003` | MinIO Web Console (Docker) | Yes — browser |

Docker uses offset ports (5433, 9002) to coexist with DBngin/homebrew services on the standard ports (5432, 9000).

---

## 8. Directory Layout (runtime)

```
scripts/vision/
├── .env                          # Environment variables (gitignored — copy from .env.example)
├── .env.example                  # Template with DBngin + Docker defaults — committed to git
├── docker-compose.yml            # Infrastructure (PostgreSQL + MinIO)
├── start.sh                      # All-in-one launcher
├── backend/
│   ├── init_db.py                # Standalone DB initialization + verification
│   ├── requirements.txt          # Python dependencies
│   ├── api/main.py               # FastAPI application
│   ├── chat/                     # Conversational agent (Agent SDK + SSE)
│   ├── core/                     # Database, CaseManager
│   ├── ingestion/                # File upload → MinIO → OCR → evidence store
│   ├── auth/                     # JWT authentication (bcrypt + users table)
│   ├── search/                   # Composable search chain
│   ├── schemas/                  # SQL migration files
│   └── tests/                    # Test suite + chat streaming test
├── frontend/
│   └── src/
│       ├── app/                  # Next.js app router pages
│       ├── components/           # Shared React components
│       └── lib/                  # API client, auth, SSE streaming
├── context-engine/               # Agent context: standards, templates, guides
├── docs/                         # Project vision and strategy docs
└── sample_files/                 # Test documents for development
```

---

## 9. Common Issues

### "connection refused" on port 5433
PostgreSQL container not running (Docker setup).
```bash
docker compose -f docker-compose.yml up -d vision-db
docker compose -f docker-compose.yml logs vision-db
```

### "connection refused" on port 5432
DBngin PostgreSQL not running. Open DBngin and click "Start" on your PostgreSQL service.

### "role 'vision' does not exist" or wrong port
`.env` doesn't match your infrastructure. For DBngin, set `VISION_DB_USERNAME` to your macOS username. For Docker, use `vision`.
```bash
# Check what the API sees
cd backend && python -c "from core.db import _DEFAULT_PORT; print(_DEFAULT_PORT)"
# Should print 5432 (DBngin) or 5433 (Docker)
```

### "claude-agent-sdk not installed"
```bash
source .venv/bin/activate && pip install claude-agent-sdk
```

### Auth returns 500
`users` table doesn't exist — schema wasn't applied. Run `python init_db.py`.

### Chat returns no assistant messages
Two possible causes:
1. The Agent SDK message type detection was using `getattr(msg, "type", "")` instead of `isinstance()` — **fixed as of 2026-06-07.**
2. `ANTHROPIC_AUTH_TOKEN` not set or invalid — check `.env`.

### MinIO bucket missing
```bash
docker compose -f docker-compose.yml up -d vision-minio-init
```

### Port already in use
```bash
lsof -ti:8400 | xargs kill -9   # kill stale API
lsof -ti:3000 | xargs kill -9   # kill stale frontend
```

### Temp filesystem full (Claude Code sessions)
Set a custom tmpdir:
```bash
export CLAUDE_CODE_TMPDIR=/tmp/claude-tmp
```

---

## 10. Reset to Zero

To completely reset the development environment:

```bash
# 1. Stop all services
cd scripts/vision
docker compose -f docker-compose.yml down -v   # destroys DB + MinIO volumes
lsof -ti:8400 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# 2. Restart infrastructure (fresh DB)
docker compose -f docker-compose.yml up -d

# 3. Wait for PostgreSQL to be ready
until PGPASSWORD=vision_dev psql -h 127.0.0.1 -p 5433 -U vision -d vision -c "SELECT 1" > /dev/null 2>&1; do sleep 1; done

# 4. Initialize schema
cd backend && source ../.venv/bin/activate && python init_db.py

# 5. Start the app
cd .. && ./start.sh
```
