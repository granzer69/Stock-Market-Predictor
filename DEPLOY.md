# Production deploy guide

## Recommended split

| Tier | Target | Notes |
|------|--------|-------|
| Web | [Vercel](https://vercel.com) | Next.js standalone or default build |
| API | Container host (Fly.io, Railway, ECS, VM) | TensorFlow + SQLite paper DB |

The UI rewrites `/api/*` to the API origin (`API_ORIGIN` / `NEXT_PUBLIC_API_URL` at build time for static export patterns; runtime uses `next.config.mjs` rewrites).

## Vercel (frontend)

**Live project (production):** [bharat-desk.vercel.app](https://bharat-desk.vercel.app) — Vercel project `bharat-desk`, root directory `frontend`, connected to `granzer69/Stock-Market-Predictor` `main`.

1. Import the repo (or use the existing project); set **Root Directory** to `frontend`.
2. **Required** environment variable (Production + Preview):
   - `API_ORIGIN` = `https://api.yourdomain.com` (HTTPS API base, **no trailing slash**)
3. `frontend/middleware.ts` proxies `/api/*` to `API_ORIGIN` at **runtime** (change the env var and redeploy; no code change).
4. On the API host, set `CORS_ORIGINS` to include your Vercel URL (e.g. `https://bharat-desk.vercel.app`).

Repo [`vercel.json`](vercel.json) sets `rootDirectory: frontend`. Local dev still uses `next.config.mjs` rewrites to `http://127.0.0.1:8000` when `API_ORIGIN` is unset in middleware (middleware returns 503 on Vercel only when unset).

The FastAPI + TensorFlow API **cannot** run on Vercel serverless; use a container host per the API section below.

**Quick API on Render (free tier):** push [`render.yaml`](render.yaml) (no disk — paper portfolio resets on restart), create a **Blueprint** from the repo on [Render](https://render.com), then set Vercel `API_ORIGIN` to the Render service URL (e.g. `https://bharat-desk-api.onrender.com`). Update `CORS_ORIGINS` on Render if your Vercel hostname differs. Paid Render plans can attach a disk + `PAPER_DB_PATH` for a persistent paper book.

## API container

Build and run:

```bash
docker build -f backend/Dockerfile -t bharat-desk-api .
docker run -p 8000:8000 \
  -e YF_DISABLE_CURL_CFFI=1 \
  -v "$(pwd)/backend/artifacts:/app/backend/artifacts" \
  -v "$(pwd)/backend/cache:/app/backend/cache" \
  bharat-desk-api
```

Optional licensed data (see `.env.example`):

```bash
-e MARKET_DATA_PROVIDER=nse_csv \
-e NSE_CSV_DIR=/data/nse_daily \
-v /path/to/csvs:/data/nse_daily:ro
```

Production browser origin (Vercel or custom domain) must be allowed on the API:

```bash
-e CORS_ORIGINS=https://desk.example.com,http://localhost:3000
```

The UI reads `GET /api/config` to show **Data: Yahoo Finance** vs **NSE CSV bundle**. No frontend env flag is required for provider selection.

## Single VM (demo)

```bash
docker compose -f docker-compose.yml up --build -d
```

Place TLS in front (Caddy/nginx) for public hosts — step-by-step in [TLS_RUNBOOK.md](TLS_RUNBOOK.md). Mount persistent volumes for `backend/cache`, `backend/artifacts`, and the paper book (see `docker-compose.yml` and [BACKUP.md](BACKUP.md)).

## Health checks

- `GET /api/health` → `{"ok": true, "model": true}`
- Structured request logs include `X-Request-Id`; research backtests are capped via `RESEARCH_MAX_CONCURRENT` (HTTP 429 when saturated).

## When Yahoo is down

1. Enable `MARKET_DATA_FAILOVER=true` (default) so the API retries missing symbols via the NSE CSV bundle when `NSE_CSV_DIR` is populated.
2. Or set `MARKET_DATA_PROVIDER=nse_csv` and mount curated daily CSVs (see [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)).
3. Validate bundles with `python backend/scripts/validate_market_data.py --dir $NSE_CSV_DIR`.

## Not in scope

Multi-region HA, autoscaling GPU training, or managed Prometheus—the desk is a research appliance.
