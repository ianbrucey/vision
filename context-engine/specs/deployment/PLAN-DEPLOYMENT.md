# Deployment — Production Docker Compose on Linode

Status: ready for implementation. Exact file paths, exact contents. Do not
deviate or invent alternatives (Commandment I/II) — if something here
conflicts with what you find in the repo, stop and ask.

Target: fresh deploy of `50.116.38.57` (currently pointed at
`vision.justicequest.pro` via an existing Cloudflare Tunnel using
`CLOUDFLARE_TUNNEL_TOKEN` from `.env`). Manual pull-and-rebuild workflow —
no CI/CD.

There is a prior attempt on the git branch `docker` (files: `Dockerfile.backend`,
`Dockerfile.frontend`, `docker-compose.yml`, `docker-entrypoint.sh`,
`.env.docker`). It is 9 commits behind current `talentlynk` HEAD and its
`docker-compose.yml`/`.env.docker` are stale (missing worker scaling, Mailgun
vars, `VISION_JWT_SECRET` wiring, MinIO public exposure). **Do not check out
or merge that branch.** Use it only as a reference for the Dockerfile shape;
create fresh files as specified below on the current branch.

---

## 1. `backend/Dockerfile` (new file)

Multi-stage not required (no build step for Python) — single stage, based on
the proven `docker` branch version:

```dockerfile
FROM python:3.13-slim

# postgresql-client: init_db wait-loop uses pg_isready.
# curl/gnupg/ca-certificates: needed to install the Node.js apt repo below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js — required because `claude_agent_sdk` (backend/requirements.txt)
# shells out to the `claude` CLI binary at runtime (see
# backend/ingestion/solicitation_triage.py, profile_synth.py,
# vendor_matching.py, enricher.py, synthesizer.py, chat/manager.py — all
# call ClaudeSDKClient, which requires the CLI on PATH).
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
```

## 2. `docker-entrypoint.sh` (new file, repo root)

Applies schema once, then starts exactly one process per container (API
container runs the API only — workers are separate containers per §4, not
backgrounded inside this script, so `docker compose up -d --scale` can scale
workers independently of the API):

```bash
#!/bin/bash
set -e

echo "Waiting for PostgreSQL (${VISION_DB_HOST}:${VISION_DB_PORT})..."
until pg_isready -h "$VISION_DB_HOST" -p "$VISION_DB_PORT" -U "$VISION_DB_USERNAME" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL ready."

cd /app/backend

if [ "$VISION_ROLE" = "worker" ]; then
    echo "Starting worker (${VISION_WORKER_ID:-worker})..."
    exec python ingestion/worker.py
else
    echo "Applying schemas..."
    python init_db.py
    echo "Starting API on :8400..."
    exec uvicorn api.main:app --host 0.0.0.0 --port 8400
fi
```

`VISION_ROLE` is a new env var read only by this script (not by any Python
code) to select API vs worker mode from the same image. Only the API
container (`VISION_ROLE` unset) runs `init_db.py`, avoiding race conditions
from multiple containers migrating concurrently.

## 3. `frontend/Dockerfile` (new file)

Uses Next.js standalone output (see `frontend/node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/output.md`)
to avoid shipping `node_modules` in the final image:

```dockerfile
FROM node:22-slim AS builder
WORKDIR /app
COPY frontend/package*.json .
RUN npm ci
COPY frontend/ .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
```

### 3a. `frontend/next.config.ts` — add `output: "standalone"`

Required for the standalone build above to produce `.next/standalone`.
Existing content must be preserved exactly, only add the new key:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  output: "standalone",
};

export default nextConfig;
```

Do **not** add the `rewrites()` proxy block seen on the `docker` branch —
current frontend code (`frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts`,
and 4 other files listed there) already reads `NEXT_PUBLIC_API_URL` directly
per-call; a rewrite would be redundant and is not part of this spec.

---

## 4. `docker-compose.prod.yml` (new file, repo root)

Extends the dev `docker-compose.yml` pattern with API, worker (x3, matching
`start.sh`'s default `VISION_WORKER_COUNT=3`), frontend, and a **second**
Cloudflare tunnel hostname for MinIO (see §5). Ports for Postgres/MinIO are
**not** published to the host in prod (only exposed on the internal Docker
network) — only `vision-frontend:3000` needs a host-mapped port, and only
because `cloudflared` is a container reaching it by service name, so even
that mapping is unnecessary. None of `vision-db`, `vision-minio`,
`vision-api`, `vision-frontend` need `ports:` in prod; they communicate over
the default Compose network by service name.

```yaml
services:
  vision-db:
    image: pgvector/pgvector:pg15
    restart: unless-stopped
    env_file: .env.prod
    environment:
      POSTGRES_DB: ${VISION_DB_DATABASE}
      POSTGRES_USER: ${VISION_DB_USERNAME}
      POSTGRES_PASSWORD: ${VISION_DB_PASSWORD}
    volumes:
      - vision_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U ${VISION_DB_USERNAME}']
      interval: 3s
      timeout: 3s
      retries: 5

  vision-minio:
    image: minio/minio:latest
    restart: unless-stopped
    command: server /data --console-address ":9003"
    env_file: .env.prod
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - vision_minio_data:/data
    healthcheck:
      test: ['CMD-SHELL', 'mc ready local']
      interval: 3s
      timeout: 3s
      retries: 5

  vision-minio-init:
    image: minio/mc:latest
    depends_on:
      vision-minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://vision-minio:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY};
      mc mb --ignore-existing local/${MINIO_BUCKET};
      echo 'MinIO bucket ready: ${MINIO_BUCKET}';
      exit 0;
      "
    env_file: .env.prod

  vision-api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env.prod
    environment:
      VISION_DB_HOST: vision-db
      MINIO_ENDPOINT: vision-minio:9000
    depends_on:
      vision-db:
        condition: service_healthy
      vision-minio:
        condition: service_healthy
    restart: unless-stopped

  vision-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env.prod
    environment:
      VISION_DB_HOST: vision-db
      MINIO_ENDPOINT: vision-minio:9000
      VISION_ROLE: worker
    depends_on:
      vision-db:
        condition: service_healthy
      vision-minio:
        condition: service_healthy
      vision-api:
        condition: service_started
    restart: unless-stopped
    deploy:
      replicas: 3

  vision-frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        NEXT_PUBLIC_API_URL: https://vision.justicequest.pro
    depends_on:
      - vision-api
    restart: unless-stopped

  vision-tunnel:
    image: cloudflare/cloudflared:latest
    command: tunnel run --token ${CLOUDFLARE_TUNNEL_TOKEN}
    env_file: .env.prod
    depends_on:
      - vision-frontend
      - vision-minio
    restart: unless-stopped

volumes:
  vision_pgdata:
  vision_minio_data:
```

Notes:
- `vision-api` sets `VISION_DB_HOST`/`MINIO_ENDPOINT` to override `.env.prod`
  defaults (which target local dev ports) — these two are the only values
  that must differ between the API/worker containers and a bare-metal run.
- `deploy.replicas: 3` requires `docker compose up -d` (not `docker-compose`
  v1) and matches `start.sh`'s `VISION_WORKER_COUNT` default. Each worker
  polls the `jobs` table independently via `SKIP LOCKED` — no config needed
  to differentiate them (see `backend/ingestion/jobs.py::claim_next` and
  `worker.py`'s `WORKER_ID = os.environ.get("VISION_WORKER_ID", f"worker-{os.getpid()}")`
  fallback, which is sufficient since each container has a distinct PID 1).
- `vision-api`'s `@app.on_event("startup")` handler in `backend/api/main.py`
  (lines 49-66) already calls all `ensure_*_schema()` functions on every
  boot — this is redundant with `init_db.py` in the entrypoint but both are
  idempotent (`IF NOT EXISTS` throughout), so no conflict.

---

## 5. Document previews — public MinIO access (human + code)

**Problem:** `GET /api/documents/{doc_id}/preview` (`backend/api/main.py`
lines 345-410) calls `ingestion/storage.py::get_public_url`, which returns a
MinIO **presigned URL** built from `MINIO_ENDPOINT` (line 101, using the
`Minio` client configured at module load from `MINIO_ENDPOINT`/`MINIO_ACCESS_KEY`/
`MINIO_SECRET_KEY`/`MINIO_SECURE` env vars, `storage.py` lines 23-36). The
browser (`frontend/src/components/DocumentPreviewModal.tsx`, lines 57-58,
163-164, 186, 211) fetches/iframes/downloads this URL **directly** — it does
not proxy through the API. In prod, `MINIO_ENDPOINT=vision-minio:9000` is a
private Docker-network hostname unreachable from the browser, so presigned
URLs must instead point at a public hostname.

**Fix — new env var, minimal code change, human tunnel config:**

1. **Human step:** Add a second public hostname to the existing Cloudflare
   Tunnel (the same tunnel identified by `CLOUDFLARE_TUNNEL_TOKEN`) —
   `files.vision.justicequest.pro` → service `vision-minio:9000` — in the
   Cloudflare Zero Trust dashboard under Networks → Tunnels → (the tunnel) →
   Public Hostname. This is dashboard-driven tunnel config, not a file in
   this repo (the tunnel is already token-based, no local `config.yml`
   exists per repo search — confirmed no `cloudflared` config file in any
   branch). **Not code — do not attempt to script this step.**

2. **Code change** — `backend/ingestion/storage.py`, function
   `get_public_url` (lines 98-106): add a new module-level var
   `_MINIO_PUBLIC_ENDPOINT = os.environ.get("MINIO_PUBLIC_ENDPOINT")` next
   to the existing config block (after line 27). In `get_public_url`,
   after generating the presigned URL from the existing internal client,
   if `_MINIO_PUBLIC_ENDPOINT` is set, rewrite the URL's host:port from
   `_MINIO_ENDPOINT` to `_MINIO_PUBLIC_ENDPOINT` (string replace on the
   generated URL — the path/query/signature are unaffected by which host
   serves the request, since MinIO validates signatures independent of the
   `Host` header). If `MINIO_PUBLIC_ENDPOINT` is unset, behavior is
   unchanged (existing dev/local behavior — presigned URL uses
   `MINIO_ENDPOINT` as today, e.g. `127.0.0.1:9002`).

3. **`.env.prod`** (§6 below) sets:
   ```
   MINIO_ENDPOINT=vision-minio:9000
   MINIO_PUBLIC_ENDPOINT=files.vision.justicequest.pro
   MINIO_SECURE=false
   ```
   `MINIO_SECURE=false` is intentional even though the public hostname is
   HTTPS — Cloudflare terminates TLS at the edge and forwards plain HTTP to
   `vision-minio:9000` inside the tunnel, same as how `vision.justicequest.pro`
   already reaches `vision-frontend:3000` over plain HTTP internally. The
   presigned URL's scheme must be rewritten to `https://` when swapping the
   host — do this as part of the same string operation (rewrite scheme +
   host together, e.g. via `urllib.parse.urlsplit`/`urlunsplit`, not naive
   string replace, so query string signing params survive intact).

---

## 6. `.env.prod` (update existing file — do not create from scratch)

`.env.prod` already exists at the repo root (gitignored, contains real
secrets) and is missing several keys. Add these (do not remove any existing
key/value not mentioned here):

```
VISION_DB_HOST=vision-db
MINIO_ENDPOINT=vision-minio:9000
MINIO_PUBLIC_ENDPOINT=files.vision.justicequest.pro
MINIO_SECURE=false
VISION_JWT_SECRET=<generate: openssl rand -hex 32>
NEXT_PUBLIC_API_URL=https://vision.justicequest.pro
CLOUDFLARE_TUNNEL_TOKEN=<copy from .env>
MAILGUN_API_KEY=<copy from .env>
MAILGUN_BASE_URL=<copy from .env>
MAILGUN_DOMAIN=<copy from .env>
MAILGUN_SANDBOX_DOMAIN=<copy from .env>
MAILGUN_WEBHOOK_SIGNING_KEY=<copy from .env>
```

`VISION_JWT_SECRET` is read by `backend/auth/__init__.py` line 29
(`os.environ.get("VISION_JWT_SECRET", "vision-dev-secret-change-in-production")`)
— the fallback dev secret must never be used in prod (Commandment-adjacent
security requirement, not optional). Generate a real random value, don't
guess or hardcode a placeholder.

Existing `.env.prod` values for `VISION_DB_DATABASE`, `VISION_DB_USERNAME`,
`VISION_DB_PASSWORD`, `VISION_DB_PORT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`,
`MINIO_BUCKET`, `DATALAB_API_KEY`, `DATALAB_API_URL`, `MISTRAL_API_KEY`,
`TAVILY_API_KEY`, `COURT_LISTENER_API_KEY`, `OPENAI_API_KEY`, `SAM_GOV_API_KEY`,
`ANTHROPIC_*` are already correct and must not be changed.

---

## 7. `deploy.sh` (new file, repo root)

Manual pull-and-rebuild script, run via SSH on the Linode box from the repo
root (`/root/vision` or wherever it's cloned — script assumes it's run from
repo root, same convention as `start.sh`):

```bash
#!/bin/bash
# ============================================================================
# Vision — Production Deploy (manual pull-and-rebuild)
# ============================================================================
# Run this ON THE SERVER after SSHing in:
#   ssh root@50.116.38.57
#   cd vision && ./deploy.sh
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/4] Pulling latest code..."
git pull

echo "[2/4] Building images..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build

echo "[3/4] Applying migrations + restarting services..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

echo "[4/4] Pruning old images..."
docker image prune -f

echo ""
echo "Deploy complete. Tailing logs (Ctrl+C to stop watching, services keep running):"
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f --tail=50
```

`chmod +x deploy.sh` after creation. No GitHub Actions, no SSH-from-laptop
automation — the human runs this manually on the box per the earlier
decision (manual script, not CI/CD).

---

## 8. Verdict (must pass before calling this "done")

Run on the Linode server after first deploy:

1. `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` —
   all services `running`/`healthy` (no `restarting` loops).
2. `curl -s https://vision.justicequest.pro/api/health` → `200` (route
   exists at `backend/api/main.py` line 725, confirmed above).
3. `curl -s https://vision.justicequest.pro/` → `200`, serves the Next.js
   app (not a Cloudflare 502).
4. Register a new user via `/register` on the live site, then log in via
   `/login` — confirms `VISION_JWT_SECRET` and Postgres connectivity work
   end-to-end through the full container stack.
5. Upload a document to a case — confirms MinIO write path
   (`vision-api` → `vision-minio:9000` internal) and worker pickup (check
   `docker compose logs vision-worker` shows a claimed/completed job).
6. Click "View Document" on an uploaded doc — confirms the presigned URL
   from `MINIO_PUBLIC_ENDPOINT` (§5) actually loads in the browser, not a
   private-hostname URL that fails to resolve.
7. `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` again
   after `git commit`+`./deploy.sh` a trivial change (e.g. this file) —
   confirms the redeploy flow doesn't require manual intervention beyond
   running the script.

If any step fails, do not mark this plan complete — report which step
failed and the exact error, don't guess a fix outside this spec's scope.

---

## 9. CORS — restrict `allow_origins` in production

**Problem:** `backend/api/main.py` lines 40-46 currently set
`allow_origins=["*"]` with an in-code comment `# tightened in production`
that was never acted on (also flagged in
`context-engine/standards/03-CODE-QUALITY/python-standards.md` line 83-85).
Wildcard origins combined with `allow_credentials=True` is permissive further
than needed once there's a single known production frontend origin.

**Fix — env-driven, defaults preserve current dev behavior:**

1. **Code change** — `backend/api/main.py`, replace lines 40-46:

   ```python
   _cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS")
   _cors_origins = (
       [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
       if _cors_origins_env
       else ["*"]
   )

   app.add_middleware(
       CORSMiddleware,
       allow_origins=_cors_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

   `os` is already imported at line 14. If `CORS_ALLOWED_ORIGINS` is unset
   (local dev, `start.sh`, `.env`), behavior is unchanged (`["*"]`).

2. **`.env.prod`** — add:
   ```
   CORS_ALLOWED_ORIGINS=https://vision.justicequest.pro
   ```

3. **Verdict addition:** after step 4 in §8 (register/login through the live
   site), open the browser devtools Network tab on
   `https://vision.justicequest.pro` and confirm API responses include
   `Access-Control-Allow-Origin: https://vision.justicequest.pro` (not `*`).
   Do not mark §9 done without this check — a typo in the env var (e.g.
   missing scheme, trailing slash) silently breaks CORS with a browser
   console error, not a server error.
