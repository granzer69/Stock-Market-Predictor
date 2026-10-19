# TLS and custom domain runbook

Use this when exposing Bharat Desk on the public internet with HTTPS. Assumes:

- **Web:** `https://desk.example.com` (Next.js)
- **API:** `https://api.desk.example.com` (FastAPI + TensorFlow)

## DNS

| Record | Points to |
|--------|-----------|
| `desk.example.com` | VM or Vercel |
| `api.desk.example.com` | VM / container host |

## Option A — Vercel (web) + VM (API)

1. Deploy frontend per [DEPLOY.md](DEPLOY.md); set `API_ORIGIN=https://api.desk.example.com`.
2. On the API host, terminate TLS with Caddy (below) on ports 80/443, proxy to `127.0.0.1:8000`.
3. Extend FastAPI CORS in `backend/main.py` to include `https://desk.example.com` (production origin).

## Option B — Single VM (Caddy + Docker Compose)

Example `Caddyfile` on the VM:

```caddy
desk.example.com {
    reverse_proxy localhost:3000
}

api.desk.example.com {
    reverse_proxy localhost:8000
}
```

```bash
docker compose up -d
caddy run --config Caddyfile
```

Caddy obtains Let's Encrypt certificates automatically when ports 80/443 are open and DNS is correct.

## Option C — nginx + certbot

```nginx
server {
    listen 443 ssl http2;
    server_name api.desk.example.com;
    ssl_certificate     /etc/letsencrypt/live/api.desk.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.desk.example.com/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Renew with `certbot renew` (cron).

## Checklist before go-live

- [ ] `GET https://api.desk.example.com/api/health` returns `ok: true`
- [ ] UI loads and `/api/*` requests succeed (no mixed-content errors)
- [ ] Paper trading disclaimer visible; no live broker keys in env
- [ ] Persistent volumes for `paper_trading.db`, `backend/cache`, `backend/artifacts`
- [ ] Rate-limit or firewall public API if needed (Vercel Firewall / cloud WAF)

## Secrets

Do not commit TLS private keys or broker credentials. Use the host’s secret store or platform env vars.
