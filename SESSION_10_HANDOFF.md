# Jerry The Customer Service Bot — Session 10 Handoff Document

**Date:** March 1, 2026
**Version:** Code v4.0.0 (main.py health) | Backend fully wired
**Status:** Production-ready backend with billing, firewall, and analytics deployed on Railway

---

## What This Project Is

Jerry The Customer Service Bot is an AI-powered customer service chatbot SaaS for Shopify stores. Store owners install via Shopify OAuth, Jerry syncs their product catalog, and customers get an AI shopping assistant that can:

- Search products semantically ("something for the beach under $50")
- Track orders (WISMO — Where Is My Order?)
- Handle returns and refunds
- Detect frustrated customers and escalate to human support (sentiment + profanity detection)
- Voice chat (STT/TTS) via browser Web Speech API
- Block prompt injection attacks via AI Firewall

**Target market:** Shopify store owners
**Pricing model:**
- Base tier: $299 AUD/mo + $0.50/resolution + 2% revenue share
- Elite tier: $1,499 AUD/mo + $1.00/resolution + 5% revenue share
**Tech stack:** Python FastAPI + Groq (Llama 3.1/3.3) + Pinecone + SentenceTransformers + Stripe + React/TypeScript
**Deployed on:** Railway (auto-deploys on push to main)

---

## Project History (Sessions 1-10)

| Session | Date | What Was Built |
|---------|------|----------------|
| 1 | Feb 14 | Product requirements document, AI architecture design |
| 2 | Feb ~15 | `conversation_engine.py` — full AI pipeline (intent, entities, LLM, escalation) |
| 3 | Feb ~18 | `product_intelligence.py` — semantic search with Pinecone + `main.py` WebSocket server |
| 4 | Feb 21 | Comprehensive audit: bug fixes, security hardening, performance optimizations |
| 5 | Feb 22 | Shopify OAuth integration, product sync, JWT auth, SQLAlchemy models |
| 6 | Feb 22 | Railway deployment, Dockerfile, ngrok tunneling, Shopify app config |
| 7 | Feb 23 | Rename to "Jerry", GraphQL product sync, order tracking, returns/refunds |
| 8 | Feb ~24 | Escalation fixes (3 iterations), frustration detection, voice chat (STT/TTS) |
| 9 | Feb ~25 | Voice bug fixes (Android TTS, stale closure, emoji stripping, voice selection) |
| 10 | Mar 1 | **Stripe billing, analytics, AI firewall (4 layers), security hardening, DB migration** |

---

## Current File Structure

```
sunsetbot/
├── railway.toml                         # Railway deploy config (Dockerfile builder)
├── SESSION_4_HANDOFF.md                 # Old handoff (Sessions 1-4)
├── SESSION_10_HANDOFF.md                # THIS FILE (current state)
│
├── backend/
│   ├── Dockerfile                       # Python 3.11-slim + PyTorch CPU-only
│   ├── main.py                          # FastAPI app v4.0.0 — WS, REST, firewall, billing
│   ├── requirements.txt                 # All deps (stripe, Pillow, filetype added in S10)
│   ├── sunsetbot.db                     # SQLite dev database
│   ├── .env                             # API keys (Groq, Pinecone, Shopify, Stripe)
│   ├── venv/                            # Python 3.11 virtual environment
│   ├── static/                          # Built widget JS bundle
│   │
│   └── app/
│       ├── __init__.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── shopify.py               # Shopify OAuth, webhooks, product sync, admin-protected
│       │   └── billing.py               # Stripe subscription creation, webhooks, usage stats
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py                # Pydantic settings (env vars, Stripe, admin key)
│       │   ├── security.py              # JWT (widget tokens), HMAC verification, admin auth
│       │   └── middleware.py             # SecurityHeadersMiddleware (HSTS, X-Frame, etc.)
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── engine.py                # Async SQLAlchemy engine + auto-migration
│       │   └── models.py                # Store, ChatSession, SupportResolution, AttributedSale
│       │
│       ├── firewall/                    # AI Agent Firewall (4 layers)
│       │   ├── __init__.py
│       │   ├── engine.py                # FirewallEngine orchestrator (scan_inbound/scan_outbound)
│       │   ├── semantic_router.py       # Vector similarity topic enforcement (cosine > 0.35)
│       │   ├── sentinel_scan.py         # LLM binary classifier for prompt injection
│       │   ├── egress_filter.py         # Canary tokens, API key leak detection, PII redaction
│       │   └── file_sanitizer.py        # Magic byte validation, EXIF stripping
│       │
│       └── services/
│           ├── __init__.py
│           ├── conversation_engine.py   # AI pipeline orchestrator (intent→entities→products→LLM)
│           ├── product_intelligence.py  # Semantic search (SentenceTransformer + Pinecone)
│           ├── analytics_service.py     # Usage tracking, resolution recording, revenue attribution
│           ├── billing_service.py       # Stripe metered billing (subscriptions, usage reports)
│           ├── order_service.py         # Order lookup, returns, refund processing
│           ├── shopify_graphql.py       # Shopify GraphQL API client
│           └── shopify_sync.py          # Product catalog sync (Shopify → Pinecone)
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── src/
        ├── main.tsx                     # Widget entry point (shadow DOM mount)
        └── Widget.tsx                   # Full chat widget (voice, TTS, product cards)
```

---

## Architecture: How Messages Flow

```
Browser (Widget.tsx — shadow DOM)
    │
    ▼ WebSocket: ws://host/ws/chat/{store_id}/{session_id}?token=jwt
    │
main.py:websocket_chat()
    ├─ JWT auth (required in production, optional in dev)
    ├─ Rate limit check (30 msgs/min)
    ├─ Connection-per-IP limit (10)
    │
    ▼ User sends: {"message": "red dresses under $60"}
    │
    ├─ 🔥 FIREWALL INBOUND SCAN
    │   ├─ SemanticRouter: cosine similarity vs 18 allowed topics (threshold 0.35)
    │   ├─ SentinelScan: Groq llama-3.1-8b-instant binary classifier
    │   └─ If blocked → send friendly redirect, skip processing
    │
    ├─ Send typing indicator
    │
    ▼
ConversationEngine.process_message()
    ├─ 1. IntentClassifier.classify()         → "product_search"
    ├─ 2. EntityExtractor.extract()           → {colors: ["red"], max_price: 60}
    ├─ 3. ProductIntelligence.search()        → [Product, Product, ...]
    ├─ 4. ResponseGenerator.generate()        → Groq API → "Here are some red dresses..."
    ├─ 5. EscalationHandler.check()           → sentiment + keyword + profanity
    ├─ 6. System prompt includes canary token → egress filter monitors for leaks
    │
    ├─ 🔥 FIREWALL OUTBOUND SCAN
    │   ├─ EgressFilter: canary token detection (hard stop)
    │   ├─ EgressFilter: API key patterns (redact)
    │   └─ EgressFilter: PII patterns (redact)
    │
    ▼ WebSocket JSON: {"type": "message", "text": "...", "products": [...]}
    │
Browser renders response + product cards + voice TTS
```

---

## AI Firewall — How It Works

The firewall sits in the WebSocket pipeline (before and after the LLM call):

### Inbound (user → Jerry)
1. **Semantic Router** — Pre-computed embeddings for 18 allowed e-commerce topics. User message is embedded and compared via cosine similarity. If max similarity < 0.35, message is off-topic → blocked.
2. **Sentinel Scan** — Groq `llama-3.1-8b-instant` binary classifier. Detects prompt injection patterns (imperative overrides, role-playing jailbreaks, encoding tricks). TRUE = safe, FALSE = malicious.
3. **Fail-open design** — If any layer errors, message is allowed through (logged for review).

### Outbound (Jerry → user)
1. **Canary Token** — Unique per-session token injected into system prompt. If it appears in Jerry's response, prompt injection succeeded → entire response blocked.
2. **API Key Detection** — Regex patterns for Shopify, OpenAI, Groq, Pinecone, Stripe keys → redacted with `[REDACTED]`.
3. **PII Detection** — Credit cards, emails, SSNs → redacted.

### Performance
- Semantic router: sub-millisecond (numpy dot product on pre-computed embeddings)
- Sentinel scan: ~200ms (Groq 8B model, fast inference)
- Shares `SentenceTransformer('all-MiniLM-L6-v2')` with ProductIntelligence — zero extra memory

---

## Services Initialized at Startup (Lifespan)

All services init in `main.py`'s `lifespan()` with graceful degradation:

| Service | Global Variable | Status |
|---------|----------------|--------|
| ConversationEngine | `conversation_engine` | Core — server won't accept WS without it |
| ProductIntelligence | `product_intelligence` | Auto-detects mock vs Pinecone mode |
| BillingService | `billing_service` | Graceful if Stripe not configured |
| AnalyticsService | `analytics_service` | Depends on billing_service reference |
| FirewallEngine | `firewall_engine` | Shares embedding_model from PI |

**Health check:** `GET /health` returns JSON with all service statuses.

---

## Database Schema (SQLite dev / PostgreSQL prod)

### `stores` table (existing + 6 new billing columns)
- Core: `shopify_domain`, `access_token`, `scopes`, `name`, `email`, `currency`
- Billing (new in S10): `stripe_customer_id`, `stripe_subscription_id`, `jerry_plan`, `monthly_interaction_limit`, `current_month_usage`, `billing_cycle_reset`
- Sync: `products_count`, `products_synced_at`, `webhook_registered`

### `chat_sessions` table (new in S10)
- `merchant_id` (FK → stores), `session_token`, `human_intervention`, `resolved`

### `support_resolutions` table (new in S10)
- `merchant_id` (FK → stores), `session_id` (FK → chat_sessions), `resolution_type`

### `attributed_sales` table (new in S10)
- `merchant_id` (FK → stores), `shopify_order_id` (unique), `order_value`, `commission_cents`

**Auto-migration:** `engine.py:_migrate_add_missing_columns()` runs at startup to ADD missing columns to existing tables (SQLAlchemy `create_all` only creates new tables).

---

## API Endpoints

### REST
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | None | Service status |
| GET | `/shopify/stores` | Admin API key | List installed stores |
| POST | `/shopify/install` | None | Start Shopify OAuth |
| GET | `/shopify/callback` | HMAC | Complete OAuth |
| POST | `/shopify/webhooks` | HMAC | Shopify webhook receiver |
| POST | `/shopify/resync/{domain}` | Admin API key | Force product resync |
| GET | `/shopify/widget-token` | None | Get JWT for widget |
| POST | `/billing/create-subscription` | None | Create Stripe subscription |
| POST | `/billing/webhooks` | Stripe sig | Stripe webhook receiver |
| GET | `/billing/usage/{domain}` | None | Current usage stats |

### WebSocket
| Path | Auth | Purpose |
|------|------|---------|
| `/ws/chat/{store_id}/{session_id}?token=jwt` | JWT (prod), optional (dev) | Real-time chat |

### Admin Authentication
Protected endpoints require `X-Admin-API-Key` header. Key is set via `ADMIN_API_KEY` env var.

---

## Environment Variables (.env)

```
# AI APIs
GROQ_API_KEY=gsk_...              # Groq LLM API
PINECONE_API_KEY=pcsk_...         # Pinecone vector DB
PINECONE_INDEX_NAME=sunsetbot-products

# Shopify
SHOPIFY_API_KEY=...               # Shopify app API key
SHOPIFY_API_SECRET=shpss_...      # Shopify app secret

# Stripe
STRIPE_SECRET_KEY=sk_test_...     # Stripe test key (configured)
STRIPE_WEBHOOK_SECRET=            # ⚠️ NOT YET CONFIGURED

# Database
DATABASE_URL=sqlite+aiosqlite:///./sunsetbot.db

# App
ENVIRONMENT=development
SECRET_KEY=local-dev-secret-key-change-in-production-abc123
ADMIN_API_KEY=dev-admin-key-change-me  # ⚠️ CHANGE FOR PRODUCTION
CORS_ORIGINS=http://localhost:5173,...
```

---

## What Was Verified Working (Session 10 Tests)

| Test | Result |
|------|--------|
| All imports (billing, analytics, firewall, middleware) | PASS |
| Server starts, all services active | PASS |
| `/health` returns billing/analytics/firewall status | PASS |
| Admin auth blocks without key (401) | PASS |
| Admin auth passes with key (200 + store data) | PASS |
| Billing usage returns 404 for unknown store | PASS |
| Normal shopping query passes through firewall | PASS |
| Prompt injection ("ignore all instructions") blocked by sentinel | PASS |
| Off-topic request ("write Python script") blocked by semantic router | PASS |

---

## What Needs Doing Next

### Immediate (Production Setup)
1. **Stripe Dashboard** — Create products/prices for Base and Elite tiers. Update placeholder `price_xxx` IDs in `billing_service.py` `PLAN_CONFIG`
2. **Stripe Webhook** — Create webhook endpoint pointing to `https://<railway-url>/billing/webhooks`, get signing secret, set `STRIPE_WEBHOOK_SECRET` env var
3. **Railway Env Vars** — Add all production env vars to Railway dashboard (especially `STRIPE_SECRET_KEY`, `ADMIN_API_KEY` with strong value)
4. **Shopify Webhook** — Run `shopify app deploy` to register `orders/create` webhook topic in Shopify Partners
5. **Test with real order** — Create test order on dev store to verify full WISMO/returns/attribution flow

### Medium Priority
6. **Store owner dashboard** — React admin panel showing conversations, analytics, escalations
7. **Landing page** — Marketing site for Jerry with pricing, demo, signup flow
8. **Onboarding flow** — Post-install wizard for store owners to configure widget
9. **Redis session persistence** — Replace in-memory context with Redis (Upstash)
10. **Automated tests** — pytest coverage for firewall, billing, conversation engine

### Future / Strategic
11. **Extract firewall to standalone product** — User wants to "pivot and create an AI agent firewall" as a separate SaaS product. Build it inside Jerry first (done), then extract to standalone repo with its own API, dashboard, and pricing.
12. **PostgreSQL migration** — Move from SQLite to PostgreSQL for production scale
13. **ElevenLabs/OpenAI TTS** — Premium voice option (current Web Speech API is OS-dependent)

---

## Commands Cheat Sheet

```bash
# Start server
cd ~/sunsetbot/backend && source venv/bin/activate && python main.py

# Health check
curl http://localhost:8000/health | python3 -m json.tool

# Test admin auth
curl -H "X-Admin-API-Key: dev-admin-key-change-me" http://localhost:8000/shopify/stores

# Build frontend widget
cd ~/sunsetbot/frontend && npm run build

# View Swagger docs
open http://localhost:8000/docs

# Deploy (auto via Railway on push)
git add -A && git commit -m "message" && git push origin main
```

---

## Important Notes

- **Branding:** Code uses "SunsetBot" in some places, "Jerry" in others. The customer-facing name is "Jerry The Customer Service Bot". Internal logger names are "sunsetbot.*" or "jerry.*".
- **Fail-open firewall:** If any firewall layer errors, messages pass through (logged). This prevents blocking legitimate customers.
- **Canary token:** Injected into LLM system prompt per session. If it leaks into output, prompt injection detected.
- **Shared embedding model:** Firewall's SemanticRouter reuses `product_intelligence.embedding_model` — saves ~80MB RAM.
- **SQLAlchemy create_all is additive only** — won't alter existing tables. That's why `_migrate_add_missing_columns()` exists in `engine.py`.
- **Currency is AUD** — Stripe billing calculations use Australian dollars. Metered pricing pushes integer cents to Stripe.
