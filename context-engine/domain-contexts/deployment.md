# Production Deployment Context

> **Purpose:** Onboard developers (human or AI) to the production deployment
> **Last Updated:** 2026-07-22
> **Maintained By:** Ian Bruce

---

## 1. Business Overview

### What This Domain Does
Vision is deployed as a Docker Compose stack on a single Linode server
(`50.116.38.57`). Caddy handles TLS termination and reverse-proxy routing for
two public hostnames. Deploys are manual via `deploy.sh` — no CI/CD.

### Key Business Rules
- [ ] **DeepSeek is the LLM backend.** The `claude` CLI installed in the backend
      container routes to DeepSeek via `ANTHROPIC_BASE_URL` /
      `ANTHROPIC_AUTH_TOKEN` env vars (set in `.env.prod`). Do not "fix" these
      to point at Anthropic.
- [ ] **No Cloudflare Tunnel.** Plain A records point both hostnames at the
      Linode IP. Caddy obtains Let's Encrypt certs automatically on boot.
- [ ] **`.env.prod` is gitignored** and contains real secrets. It lives only
      on the server at `/root/vision-new/.env.prod`. Never commit it.
- [ ] **1 worker replica** (not 3) — the server has 1.9GB RAM. Scaling up
      workers requires more RAM.
- [ ] **Old deployment preserved** at `/root/vision/` (rsync'd, not git).
      The active deployment is at `/root/vision-new/` (git clone, branch
      `talentlynk`). Do not delete the old directory without confirming.

### User Stories This Supports
- As a developer, I can deploy updates by SSHing in and running `./deploy.sh`
- As an agent, I can check deployment status via SSH commands

---

## 2. Code Navigation Guide

> **Start here when working on deployment**

### Entry Points
| If you want to... | Start at... | Then follow... |
|-------------------|-------------|----------------|
| Deploy an update | SSH → `cd /root/vision-new` → `./deploy.sh` | Watch logs, Ctrl+C when stable |
| Check service health | `docker compose -f docker-compose.prod.yml ps` | Look for `healthy` / `running` |
| View logs | `docker compose -f docker-compose.prod.yml logs -f --tail=50` | Ctrl+C to stop |
| Modify routing/TLS | `Caddyfile` (repo root) | Rebuild only caddy: `docker compose up -d vision-caddy` |
| Add an env var | `.env.prod` (server only, gitignored) | Restart affected service |
| Change the compose stack | `docker-compose.prod.yml` (repo root) | Rebuild + `up -d` |

### Key Files (Read These First)
| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Service definitions: db, minio, api, worker, frontend, caddy |
| `Caddyfile` | Reverse proxy rules + auto-HTTPS for both hostnames |
| `backend/Dockerfile` | Python 3.13 + Node 22 (claude CLI) + deps |
| `frontend/Dockerfile` | Next.js standalone build |
| `docker-entrypoint.sh` | `VISION_ROLE` switch: API vs worker from same image |
| `deploy.sh` | `git pull` → `build` → `up -d` → `prune` → `logs -f` |
| `.env.prod` | All secrets (server-only, gitignored) |

### File Relationships (How Data Flows)
```
Browser (HTTPS)
    ↓
Caddy (:80/:443) — TLS termination
    ↓
    ├─ vision.justicequest.pro/    → vision-frontend:3000 (Next.js)
    ├─ vision.justicequest.pro/api → vision-api:8400 (FastAPI)
    └─ files.vision.justicequest.pro → vision-minio:9000 (presigned URLs)

Internal Docker network:
    vision-api ──→ vision-db:5432 (Postgres + pgvector)
    vision-api ──→ vision-minio:9000 (file storage)
    vision-worker ──→ vision-db + vision-minio (same as API)
```

---

## 3. Infrastructure

### Server
| Property | Value |
|----------|-------|
| IP | `50.116.38.57` |
| OS | Ubuntu 6.8.0 (x86_64) |
| RAM | 1.9 GB |
| Disk | 49 GB (35 GB used) |
| Docker | 29.6.1 |
| Compose | v5.2.0 |
| SSH key | `~/.ssh/vision` (local Mac) |
| SSH command | `ssh vision` (config entry in `~/.ssh/config`) or `./ssh-vision.sh` |

### Directories on Server
| Path | What |
|------|------|
| `/root/vision-new/` | Active deployment (git clone, branch `talentlynk`) |
| `/root/vision/` | Old deployment (rsync'd, stopped — backup only) |
| `/root/deploy-build.log` | Build log from last `deploy.sh` run |

### Public Hostnames (A records → 50.116.38.57)
| Hostname | Routes To | Purpose |
|----------|-----------|---------|
| `vision.justicequest.pro` | Caddy → frontend + `/api/*` → API | Main app |
| `files.vision.justicequest.pro` | Caddy → MinIO :9000 | Browser-accessible presigned URLs |

### Docker Services (docker-compose.prod.yml)
| Service | Image | Purpose |
|---------|-------|---------|
| `vision-db` | `pgvector/pgvector:pg15` | Postgres + pgvector + pg_trgm |
| `vision-minio` | `minio/minio:latest` | S3-compatible file storage |
| `vision-minio-init` | `minio/mc:latest` | One-shot: creates bucket on boot |
| `vision-api` | built from `backend/Dockerfile` | FastAPI on :8400 |
| `vision-worker` | built from `backend/Dockerfile` | Ingestion worker (`VISION_ROLE=worker`) |
| `vision-frontend` | built from `frontend/Dockerfile` | Next.js standalone on :3000 |
| `vision-caddy` | `caddy:2-alpine` | TLS + reverse proxy on :80/:443 |

### Docker Volumes
| Volume | What |
|--------|------|
| `vision_pgdata` | Postgres data (persistent) |
| `vision_minio_data` | MinIO/uploaded files (persistent) |
| `vision_caddy_data` | Caddy TLS certs + state |
| `vision_caddy_config` | Caddy config cache |

---

## 4. Environment Variables (.env.prod)

Lives at `/root/vision-new/.env.prod` on the server (gitignored, not in the
repo). Contains all secrets. Key groups:

| Group | Variables | Notes |
|-------|-----------|-------|
| Database | `VISION_DB_HOST` (`vision-db`), `_PORT`, `_DATABASE`, `_USERNAME`, `_PASSWORD` | Internal Docker hostname |
| LLM (DeepSeek) | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `_OPUS_`, `_SONNET_`, `_HAIKU_` | Points at `api.deepseek.com/anthropic` |
| MinIO | `MINIO_ENDPOINT` (`vision-minio:9000`), `_PUBLIC_ENDPOINT` (`files.vision.justicequest.pro`), `_ACCESS_KEY`, `_SECRET_KEY`, `_BUCKET`, `_SECURE` (`false`) | Internal for API, public for browser |
| JWT | `VISION_JWT_SECRET` | Generated via `openssl rand -hex 32` |
| CORS | `CORS_ALLOWED_ORIGINS` (`https://vision.justicequest.pro`) | Restricts API to frontend origin |
| Frontend | `NEXT_PUBLIC_API_URL` (`https://vision.justicequest.pro`) | Baked into Next.js build via Docker arg |
| Mailgun | `MAILGUN_API_KEY`, `_BASE_URL`, `_DOMAIN`, `_SANDBOX_DOMAIN`, `_WEBHOOK_SIGNING_KEY` | Outbound + inbound email |
| Other APIs | `DATALAB_*`, `MISTRAL_*`, `TAVILY_*`, `COURT_LISTENER_*`, `OPENAI_*`, `SAM_GOV_*` | Same keys as local `.env` |

To update an env var: edit `.env.prod` on the server, then rebuild/restart
the affected service. `NEXT_PUBLIC_API_URL` requires a frontend rebuild
(it's a build-time arg).

---

## 5. Deploy Workflow

### First-time Deploy (already done)
1. SSH in: `ssh -i ~/.ssh/vision root@50.116.38.57`
2. Clone: `git clone https://github.com/ianbrucey/vision.git /root/vision-new`
3. Checkout branch: `git checkout talentlynk`
4. Copy `.env.prod` to `/root/vision-new/` (contains all secrets)
5. Stop old stack: `cd /root/vision && docker compose -f docker-compose.prod.yml down`
6. Stop nginx (conflicts with Caddy on :80/:443): `systemctl stop nginx && systemctl disable nginx`
7. Build + start: `cd /root/vision-new && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`

### Routine Update Deploy
```bash
ssh -i ~/.ssh/vision root@50.116.38.57
cd /root/vision-new
./deploy.sh
```
`deploy.sh` does: `git pull` → `docker compose build` → `up -d` → `prune` → `logs -f`

### How Another Agent Can Access the Server
The SSH key at `~/.ssh/vision` is already authorized on the server. An SSH
config entry `Host vision` has been added to `~/.ssh/config`, and a wrapper
script `ssh-vision.sh` exists at the repo root. No password needed.

```bash
# Interactive shell (any of these work):
ssh vision
./ssh-vision.sh

# Run a single command without opening a shell:
ssh vision "docker compose -f /root/vision-new/docker-compose.prod.yml ps"
./ssh-vision.sh "docker compose -f /root/vision-new/docker-compose.prod.yml ps"

# Check service status:
ssh vision "cd /root/vision-new && docker compose -f docker-compose.prod.yml ps"

# Tail logs:
ssh vision "cd /root/vision-new && docker compose -f docker-compose.prod.yml logs -f --tail=50"

# Tail specific service:
ssh vision "cd /root/vision-new && docker compose -f docker-compose.prod.yml logs -f vision-api"
ssh vision "cd /root/vision-new && docker compose -f docker-compose.prod.yml logs -f vision-worker"
ssh vision "cd /root/vision-new && docker compose -f docker-compose.prod.yml logs -f vision-caddy"

# Restart a single service:
ssh vision "cd /root/vision-new && docker compose -f docker-compose.prod.yml restart vision-api"

# Check health endpoint:
ssh vision "curl -s https://vision.justicequest.pro/api/health"

# Check if build is still running:
ssh vision "ps aux | grep 'docker compose' | grep -v grep; tail -20 /root/deploy-build.log"
```

---

## 6. Common Tasks (How-To)

### "I need to deploy a code change"
1. Commit + push to `talentlynk` on GitHub
2. SSH to server, run `cd /root/vision-new && ./deploy.sh`
3. Watch the logs until services are stable, Ctrl+C

### "I need to add a new env var"
1. SSH to server: `ssh -i ~/.ssh/vision root@50.116.38.57`
2. Edit: `nano /root/vision-new/.env.prod`
3. Restart affected service: `docker compose -f docker-compose.prod.yml up -d vision-api`
4. If it's a `NEXT_PUBLIC_*` var, rebuild frontend: `docker compose -f docker-compose.prod.yml up -d --build vision-frontend`

### "I need to check if the deploy succeeded"
1. `docker compose -f docker-compose.prod.yml ps` — all services `running`/`healthy`
2. `curl -s https://vision.justicequest.pro/api/health` → `{"status":"ok"}`
3. `curl -s https://vision.justicequest.pro/` → HTML (not 502)

### "I need to roll back to the old deployment"
```bash
cd /root/vision-new && docker compose -f docker-compose.prod.yml down
systemctl start nginx
cd /root/vision && docker compose -f docker-compose.prod.yml up -d
```

### "I need to run a database migration"
Migrations run automatically on API container boot via `init_db.py` in
`docker-entrypoint.sh`. All schemas use `IF NOT EXISTS` (idempotent). To
force a re-run: `docker compose -f docker-compose.prod.yml restart vision-api`

---

## 7. Known Issues & Technical Debt

- [ ] **Worker replicas capped at 1** — server has 1.9GB RAM. Scaling to 3
      workers (as `start.sh` defaults for local dev) will OOM. Upgrade server
      RAM or move workers to a separate host.
- [ ] **Old deployment at `/root/vision/`** — still on disk (35 GB used
      total). Safe to delete once the new deployment is confirmed stable,
      but confirm with the user first.
- [ ] **MinIO console not exposed** — `vision-minio` runs with
      `--console-address ":9003"` but Caddy only proxies the S3 API port
      (:9000) at `files.vision.justicequest.pro`. The console is accessible
      only inside the Docker network.
- [ ] **`deploy.sh` runs `git pull`** — if there are uncommitted changes on
      the server (shouldn't be, but possible), the pull will fail. The script
      uses `set -e` so it will stop.

---

## 8. Related Domains

| Domain | Relationship | Context File |
|--------|--------------|--------------|
| Workspace | File storage uses MinIO (deployed here) | `domain-contexts/workspace.md` (via SKILL.md) |
| Agent SDK | Claude CLI in backend container uses DeepSeek | `domain-contexts/agent-tool-building.md` |
| External Integrations | Mailgun, DataLab, etc. — keys in `.env.prod` | `domain-contexts/external-integrations.md` |

---

> ⚠️ **When working on deployment:** Always check `docker compose ps` before
> making changes. Never delete `/root/vision/` (old backup) without
> confirmation. Never commit `.env.prod`.
 |
