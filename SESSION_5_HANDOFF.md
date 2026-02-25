# Jerry The Customer Service Bot — Session 5 Handoff Document

**Date:** February 22, 2026
**Version:** Code v3.0.0 (main.py) / v1.2.0 (services) / v1.0.0 (Shopify + DB + Auth)
**Status:** Shopify OAuth working. App installed on dev store. React widget built. Ready for test products + deployment.

---

## What Happened This Session

Session 5 was the **Shopify integration session** — the biggest single-session build in the project. We went from "working chatbot backend" to "full Shopify-installable app with embeddable widget."

### Built in This Session

1. **Database Layer** (`app/db/`)
   - `engine.py` — Async SQLAlchemy engine (SQLite dev / PostgreSQL prod), session factory, `init_db()` / `close_db()`
   - `models.py` — `Store` model (shop domain, access token, name, email, plan, sync timestamps, active flag)

2. **Core Config & Auth** (`app/core/`)
   - `config.py` — Centralized Pydantic BaseSettings replacing all scattered `os.getenv()` calls. Includes `app_url` property that reads `APP_URL` env var (for ngrok in dev) or constructs from Railway domain in prod.
   - `security.py` — JWT create/verify for widget tokens + Shopify HMAC verification for OAuth callbacks and webhooks

3. **Shopify OAuth + Webhooks** (`app/api/shopify.py`)
   - `GET /shopify/install?shop=xxx.myshopify.com` — Redirects to Shopify OAuth consent screen
   - `GET /shopify/callback` — Exchanges auth code for access token, verifies HMAC, saves store to DB
   - `GET /shopify/widget-token?shop=xxx` — Returns JWT for chat widget WebSocket auth
   - `POST /shopify/webhooks` — Receives product create/update/delete + app/uninstalled events
   - `GET /shopify/stores` — Lists all installed stores (admin endpoint)

4. **Product Sync** (`app/services/shopify_sync.py`)
   - `ShopifySyncService` — Fetches all products via paginated Shopify REST API (250/page)
   - Converts Shopify product format → `CatalogProduct` (extracts variants, prices, sizes, colors, materials)
   - Webhook handler for individual product events (create/update/delete)
   - `register_webhooks()` — Sets up webhooks after install
   - Products prefixed with `shopify-{id}` to avoid ID collisions with mock data

5. **React Chat Widget** (`frontend/`)
   - Built with React 18 + TypeScript + Vite
   - Compiles to single IIFE file: `backend/static/sunsetbot-widget.iife.js` (49KB gzipped)
   - Shadow DOM for CSS isolation from host page
   - Floating chat bubble → expandable chat panel
   - Product cards with images, prices, "View" buttons
   - Typing indicator, auto-scroll, mobile responsive
   - Configurable via `data-*` attributes: `data-shop`, `data-server`, `data-color`, `data-position`
   - Auto-reconnects with exponential backoff (max 5 attempts)
   - Falls back to demo mode if widget-token endpoint returns 404

6. **main.py v3.0.0**
   - Settings-based config (replaced all `os.getenv()`)
   - Database init/shutdown in lifespan
   - Shopify router mounted
   - Static file serving for widget JS + demo page
   - JWT WebSocket auth (required in production, optional in development)

7. **Demo Page** (`backend/static/demo.html`)
   - Fake store page with sample product cards
   - Widget script tag embedded — shows how store owners would use it

### Bugs Found & Fixed During OAuth Testing

Two critical bugs in Shopify HMAC verification:

1. **Missing query params** — OAuth callback manually listed expected params (`code`, `shop`, `state`, `hmac`, `timestamp`) but Shopify sends additional params (like `host`). Fixed by reading ALL params from `request.query_params`.

2. **URL-encoding mismatch** — Used `urlencode()` which encodes special chars (`:` → `%3A`), but Shopify's HMAC format uses raw `key=value` pairs joined with `&`. Fixed by replacing `urlencode(params_to_sign)` with `"&".join(f"{k}={v}" for k, v in params_to_sign.items())`.

### Infrastructure Set Up

- **Shopify Partner account** created and linked
- **Dev store:** `sunsetbot.myshopify.com`
- **App:** Jerry The Customer Service Bot (Client ID: `b323444b85e59301f81c74e556dd7efe`)
- **Custom Distribution** configured (not App Store) — install links generated in Partner dashboard
- **Legacy install flow** enabled
- **ngrok** (v3.36.1) installed for HTTPS tunneling
- **Shopify CLI** (v3.91.0) installed globally via npm
- **shopify.app.toml** created with app config
- **Railway account** created, linked to GitHub (not yet deployed)

---

## Current File Structure

```
sunsetbot/
├── CLAUDE.md                            # Project instructions (updated Session 5)
├── SESSION_4_HANDOFF.md                 # Session 1-4 history
├── SESSION_5_HANDOFF.md                 # THIS FILE
├── shopify.app.toml                     # Shopify app config (used by Shopify CLI)
├── backend/
│   ├── main.py                          # FastAPI app, WebSocket, REST endpoints (v3.0.0)
│   ├── requirements.txt                 # Python dependencies (includes PyJWT)
│   ├── test_chat.html                   # Browser-based chat test UI (legacy)
│   ├── .env                             # API keys — NEVER commit
│   ├── sunsetbot.db                     # SQLite database (auto-created on startup)
│   ├── venv/                            # Python virtual environment (Python 3.11)
│   ├── static/
│   │   ├── sunsetbot-widget.iife.js     # Built React widget (49KB gzipped)
│   │   └── demo.html                    # Demo page showing the widget
│   └── app/
│       ├── __init__.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── conversation_engine.py   # AI pipeline orchestrator (v1.2.0)
│       │   ├── product_intelligence.py  # Semantic search + product catalog (v1.2.0)
│       │   └── shopify_sync.py          # Shopify product sync service (v1.0.0)
│       ├── api/
│       │   ├── __init__.py
│       │   └── shopify.py               # Shopify OAuth + webhooks (v1.0.0)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py                # Pydantic Settings (all env vars) (v1.0.0)
│       │   └── security.py              # JWT + Shopify HMAC verification (v1.0.0)
│       └── db/
│           ├── __init__.py
│           ├── models.py                # SQLAlchemy Store model (v1.0.0)
│           └── engine.py                # Async DB engine + session factory (v1.0.0)
└── frontend/
    ├── package.json
    ├── node_modules/                    # npm dependencies (installed)
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx                     # Widget entry point (shadow DOM mount)
        └── Widget.tsx                   # React chat widget component
```

---

## What Works Right Now

### Starting the Server
```bash
cd ~/sunsetbot/backend
source venv/bin/activate
python main.py
# Server: http://localhost:8000
# Swagger: http://localhost:8000/docs
# Widget demo: http://localhost:8000/static/demo.html
```

### Verified Working
- Health check: `curl http://localhost:8000/health` → all services ready
- WebSocket chat: products returned for "what shoes do you have?"
- Widget JS served: `GET /static/sunsetbot-widget.iife.js` → 200
- Demo page: `GET /static/demo.html` → 200
- Shopify OAuth: Full install flow tested end-to-end → app installed on dev store
- Store list: `GET /shopify/stores` → returns 1 installed store (sunsetbot.myshopify.com)

### For Shopify OAuth Testing (needs HTTPS)
```bash
# Terminal 1: Start backend
cd ~/sunsetbot/backend && source venv/bin/activate && python main.py

# Terminal 2: Start ngrok tunnel
ngrok http 8000
# Copy the HTTPS URL (e.g., https://xxx.ngrok-free.dev)

# Update .env: set APP_URL to the ngrok URL
# Update CORS_ORIGINS to include the ngrok URL

# Visit: https://<ngrok-url>/shopify/install?shop=sunsetbot.myshopify.com
```

---

## API Endpoints (16 total)

```
GET  /                                 Root info (version, status)
GET  /health                           Service health check
GET  /docs                             Swagger UI

# Shopify
GET  /shopify/install                  Start OAuth install flow
GET  /shopify/callback                 OAuth callback (exchange code for token)
GET  /shopify/widget-token             Get JWT for chat widget
POST /shopify/webhooks                 Receive product/app webhooks
GET  /shopify/stores                   List installed stores (admin)

# WebSocket
WS   /ws/chat/{store_id}/{session_id}?token=xxx

# Products
POST /api/products/index               Index products into vector DB
DEL  /api/products/{product_id}        Remove product from index

# Sessions
DEL  /api/sessions/{session_id}        End a session
GET  /api/sessions/active              List active sessions

# Static
GET  /static/sunsetbot-widget.iife.js  Widget JS bundle
GET  /static/demo.html                 Widget demo page
```

---

## Critical Patterns — Don't Break These

### Shopify HMAC Verification
- OAuth callback reads ALL query params via `request.query_params` (not manually listed)
- HMAC format: sorted key=value pairs joined with `&` — **NO url-encoding**
- Webhook HMAC uses `X-Shopify-Hmac-Sha256` header with base64-encoded HMAC of raw body

### Service Initialization
- All services init in `lifespan` context manager (NOT at module level)
- `lifespan` function MUST be defined BEFORE the `FastAPI()` constructor
- If a service fails to init, server starts in degraded mode

### JWT Auth
- Widget gets JWT from `/shopify/widget-token` containing `store_id` + `session_id`
- Production: JWT required for WebSocket — rejects without valid token
- Development: JWT optional — connections work without token
- 24-hour expiry (configurable via `jwt_expiry_hours` in Settings)

### Settings
- All env vars centralized in `app/core/config.py` via Pydantic BaseSettings
- Use `get_settings()` to access — it's cached
- `settings.is_production` / `settings.is_development` for env checks
- `settings.shopify_configured` checks if Shopify API key+secret are set
- `settings.app_url` reads `APP_URL` env var or constructs default

### Widget
- Single IIFE file, no external dependencies
- Shadow DOM for CSS isolation
- Reads config from `data-*` attributes on `<script>` tag
- Falls back to demo mode when widget-token unavailable

---

## Shopify Account Details

- **Partner account:** Linked (created Feb 22, 2026)
- **Dev store domain:** `sunsetbot.myshopify.com`
- **App name:** Jerry The Customer Service Bot
- **App Client ID:** `b323444b85e59301f81c74e556dd7efe`
- **App Client Secret:** In `.env` as `SHOPIFY_API_SECRET`
- **Distribution:** Custom distribution (install link from Partner dashboard)
- **Legacy install flow:** Enabled
- **App installed on dev store:** YES (Feb 22, 2026)
- **Dev store has 0 products** — needs test products added

---

## What Needs Building Next (Prioritized)

### 1. Add Test Products to Dev Store (Quick Win)
The dev store has 0 products. Add 10-20 test products in Shopify admin (`sunsetbot.myshopify.com/admin/products`), then trigger a product sync to test the full pipeline:
- Shopify product sync → CatalogProduct conversion → Pinecone indexing
- Customer asks "show me red dresses" → real products returned from Shopify catalog

### 2. Railway Deployment (Get it Live)
- Create `backend/Dockerfile` (Python 3.11 slim, install deps, run uvicorn)
- Create `backend/railway.toml` (build command, start command, health check)
- Push to GitHub, connect to Railway
- Set production env vars in Railway dashboard (DATABASE_URL for PostgreSQL, etc.)
- Update Shopify app URLs to Railway domain (replace ngrok)

### 3. Redis Session Persistence
- Replace `_InMemoryContextManager` with `RedisContextManager`
- `ConversationContext.to_json()` / `from_json()` already work — just wire up Redis
- Use Upstash Redis (free tier) or Railway Redis add-on

### 4. Store-Specific Configuration
- Load store name, policies, and branding from DB into ConversationEngine
- Currently uses hardcoded defaults (StoreConfig)
- Each store should have its own return policy, shipping info, brand voice

### 5. Billing / Shopify App Store
- Usage metering
- Shopify Billing API integration ($199/mo plan)
- Move from Custom Distribution to App Store listing

### 6. Store Owner Dashboard
- React admin panel: analytics, conversation viewer, escalation alerts
- REST API endpoints for dashboard data

### 7. Automated Tests
- No pytest tests exist yet
- Smoke tests exist in `if __name__ == "__main__"` blocks
- Priority: OAuth flow tests, WebSocket auth tests, product sync tests

---

## Environment Variables (.env)

```
GROQ_API_KEY=<real key present>
PINECONE_API_KEY=<real key present>
PINECONE_ENVIRONMENT=your_pinecone_environment_here
PINECONE_INDEX_NAME=sunsetbot-products
SHOPIFY_API_KEY=b323444b85e59301f81c74e556dd7efe
SHOPIFY_API_SECRET=<real secret present>
DATABASE_URL=sqlite+aiosqlite:///./sunsetbot.db
REDIS_URL=                                          # empty — using in-memory
ENVIRONMENT=development
SECRET_KEY=local-dev-secret-key-change-in-production-abc123
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://subexternal-undelighted-sherron.ngrok-free.dev
APP_URL=https://subexternal-undelighted-sherron.ngrok-free.dev
SENTRY_DSN=
```

**Note:** ngrok URLs are ephemeral. When starting a new ngrok session, you'll get a new URL. Update `APP_URL` and `CORS_ORIGINS` in `.env`, and update the URLs in the Shopify app config (via Partner dashboard or `shopify.app.toml`).

---

## Session History

- **Session 1 (Feb 14):** PRD, architecture doc, branding
- **Session 2 (Feb ~15):** conversation_engine.py — full AI pipeline
- **Session 3 (Feb ~18):** product_intelligence.py + main.py + test_chat.html
- **Session 4 (Feb 21):** Comprehensive audit — 8 bugs fixed, security hardening, performance optimization
- **Session 5 (Feb 22):** Shopify integration (OAuth, product sync, webhooks), JWT auth, database layer, React chat widget, centralized settings. **OAuth tested and working — app installed on dev store.**
