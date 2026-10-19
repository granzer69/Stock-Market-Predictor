# Production deploy guide

## Recommended split

| Tier | Target | Notes |
|------|--------|-------|
| Web | [Vercel](https://vercel.com) | Next.js standalone or default build |
| API | Container host (Fly.io, Railway, ECS, VM) | TensorFlow + SQLite paper DB |

The UI rewrites `/api/*` to the API origin (`API_ORIGIN` / `NEXT_PUBLIC_API_URL` at build time for static export patterns; runtime uses `next.config.mjs` rewrites).

## Vercel (frontend)

1. Import the repo; set **Root Directory** to `frontend`.
2. Environment variable for preview/production:
   - `API_ORIGIN` = `https://api.yourdomain.com` (HTTPS API base, no trailing slash)
3. Build command: `pnpm build` · Output: Next default (standalone optional).

Example [`vercel.json`](vercel.json) sets the rewrite when `API_ORIGIN` is injected at deploy time via project settings (see file comments).

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

The UI reads `GET /api/config` to show **Data: Yahoo Finance** vs **NSE CSV bundle**. No frontend env flag is required for provider selection.

## Single VM (demo)

```bash
docker compose -f docker-compose.yml up --build -d
```

Place TLS in front (Caddy/nginx) for public hosts — step-by-step in [TLS_RUNBOOK.md](TLS_RUNBOOK.md). Paper SQLite lives in the container unless you mount `backend/paper_trading.db`.

## Health checks

- `GET /api/health` → `{"ok": true, "model": true}`
- Monitor Yahoo failures via logs; switch to `nse_csv` when CSVs are available.

## Not in scope

Multi-region HA, autoscaling GPU training, or managed Prometheus—the desk is a research appliance.
