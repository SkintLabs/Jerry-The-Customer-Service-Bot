# SunsetBot — Session 4 Handoff Document

**Date:** February 21, 2026
**Version:** Code v2.2.0 (main.py) / v1.2.0 (services)
**Status:** MVP backend complete — ready for Shopify integration + React frontend

---

## What This Project Is

SunsetBot is an AI-powered customer service chatbot for Shopify stores. Store owners install it, it syncs their product catalog, and their customers get an AI shopping assistant that can:

- Search products semantically ("something for the beach under $50")
- Answer sizing, shipping, return policy questions from store config
- Detect frustrated customers and escalate to human support
- Track conversation context across a session

**Target market:** Shopify store owners. Planned pricing: $199/mo.
**Tech stack:** Python FastAPI + Groq (Llama 3.1) + Pinecone + SentenceTransformers. Frontend will be React/TypeScript.

---

## Project History

### Session 1 (Feb 14)
- Created product requirements document (70+ pages)
- Defined AI architecture, tech stack decisions
- Set up project guidelines and branding (Golden Hour / SunsetBot)

### Session 2 (Feb ~15)
- Built `conversation_engine.py` — full AI pipeline:
  - IntentClassifier (keyword-based, 6 intents)
  - EntityExtractor (regex: price, size, color, material, category)
  - ResponseGenerator (Groq/Llama 3.1 with dynamic prompts)
  - EscalationHandler (sentiment + keyword triggers)
  - Mock product catalog for testing
- All data models: Message, Product, CartItem, StoreConfig, ConversationContext
- Smoke test harness

### Session 3 (Feb ~18)
- Built `product_intelligence.py` — semantic product search:
  - SentenceTransformer embeddings (all-MiniLM-L6-v2, 384-dim)
  - Pinecone integration (with mock fallback)
  - 20-product demo catalog with rich metadata
  - Multi-factor re-ranking (relevance + inventory + velocity + price)
- Built `main.py` — full WebSocket server:
  - `/ws/chat/{store_id}/{session_id}` endpoint
  - Welcome message, typing indicators, error handling
  - REST endpoints: `/health`, `/api/products/index`, `/api/sessions/active`
- Built `test_chat.html` — browser-based chat test UI

### Session 4 prep (Feb 21 — this session)
**Comprehensive audit and hardening of all code:**

#### Bugs Fixed
- **Groq model decommissioned** — `llama-3.1-70b-versatile` no longer exists. Updated to `llama-3.3-70b-versatile`
- `asyncio.get_event_loop()` → `asyncio.get_running_loop()` (Python 3.12+ compat)
- Plural normalization bug: `.rstrip("s")` mangled "dress" → "dre"; now uses proper singular detection
- `cart_items` was not serialized in `to_json()`/`from_json()` — fixed
- `import json` was inside WebSocket message loop — moved to module level
- `.env` file had stray triple-backtick at end — removed
- Size regex matched bare numbers ("3 dresses" → size "3") — now requires "size" prefix or letter sizes
- `lifespan` function was referenced before definition — reordered

#### Security Hardening
- WebSocket message rate limiting (30 msgs/min per session)
- Max concurrent connections per IP (10)
- WebSocket message size limit (8 KB per frame)
- CORS wildcard + credentials validation (auto-disables credentials if `*`)
- Duplicate session handling (closes old WebSocket, notifies client)
- Message length validation (max 2000 chars in conversation engine)
- Prompt injection mitigation (user input wrapped in XML delimiters in LLM prompt)
- LLM system prompt includes explicit instruction not to follow user-embedded instructions

#### Performance Improvements
- Product embeddings pre-computed at startup and cached (was re-embedding per search)
- Dedicated thread pool executors for embeddings vs Pinecone I/O
- Pinecone query timeout (10s) with graceful fallback
- History capped at 50 messages per session
- Viewed products capped at 200 per session

#### Architecture Improvements
- Module-level init → `lifespan` context manager (FastAPI modern pattern)
- Graceful shutdown: closes all WebSocket connections cleanly
- `/health` returns 200 even when degraded (reports per-service status)
- Service unavailability returns 503 on REST, closes WS with 1011
- Mock search now filters by color, category, and min_price (was max_price only)
- Pinecone filter builder supports price ranges (`$gte` + `$lte`)
- Added occasion/season entity extraction (beach, summer, gym, etc.)
- Added more materials (bamboo, cashmere, nylon) and attributes (packable, quick-dry)
- Requirements.txt uses version ranges instead of pinned versions
- Removed unused dependencies (aioredis, structlog, transformers)

---

## Current File Structure

```
sunsetbot/
├── backend/
│   ├── main.py                          # FastAPI app, WebSocket, REST endpoints (v2.2.0)
│   ├── requirements.txt                 # Python dependencies
│   ├── test_chat.html                   # Browser chat test UI
│   ├── .env                             # API keys and config
│   ├── venv/                            # Python virtual environment
│   └── app/
│       ├── __init__.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── conversation_engine.py   # AI pipeline orchestrator (v1.2.0)
│       │   └── product_intelligence.py  # Vector search + product catalog (v1.2.0)
│       ├── api/
│       │   └── __init__.py              # Empty — for future route modules
│       ├── core/
│       │   └── __init__.py              # Empty — for config, auth, utils
│       └── db/
│           └── __init__.py              # Empty — for SQLAlchemy models
│
├── SESSION_4_HANDOFF.md                 # THIS FILE
│
└── (frontend/ — NOT CREATED YET)
```

---

## What Works Right Now

Start the server and test:

```bash
cd ~/sunsetbot/backend
source venv/bin/activate
python main.py
```

Then open `test_chat.html` in a browser. You can:

1. Ask about products: "Show me boots under $130" → returns semantically-matched products
2. Ask about sizing: "Do the Chelsea boots run true to size?"
3. Ask about policies: "What's your return policy?" → answers from StoreConfig
4. Report issues: "I received the wrong item" → triggers escalation detection
5. Casual chat: "Hi there!" → friendly greeting response

**What you'll see:**
- Typing indicator while AI thinks
- Bot response with intent badge
- Product cards with price and stock info
- WebSocket debug log at bottom

---

## What Needs Building Next (Session 4+ priorities)

### Priority 1: JWT Authentication for WebSocket
**Why:** Currently anyone can connect with any store_id/session_id. This is the single biggest security gap.

**Approach:**
1. Add `POST /api/auth/session-token` endpoint
2. Client calls it with Shopify shop domain + customer info
3. Returns a signed JWT with `store_id`, `session_id`, expiry
4. WebSocket connects with `?token=<jwt>` query parameter
5. Server validates JWT before accepting connection

**Files to create/modify:**
- `app/core/auth.py` — JWT encode/decode, validation
- `main.py` — add token query param to WebSocket, add `/api/auth/session-token`

### Priority 2: Shopify Integration
**Why:** The entire product is built for Shopify. Without this, it's just a demo.

**Approach:**
1. Shopify OAuth flow for store installation
2. Product catalog sync via Admin API → index into Pinecone
3. Webhook receiver for product create/update/delete
4. Order tracking via Admin API
5. Store config loaded from Shopify store metadata

**Files to create:**
- `app/services/shopify_integration.py` — OAuth, product sync, webhooks
- `app/api/shopify_routes.py` — `/auth/shopify`, `/webhooks/shopify`

### Priority 3: React Chat Widget
**Why:** `test_chat.html` is for dev testing. Customers need a polished embeddable widget.

**Approach:**
1. React + TypeScript + Vite
2. Embeddable `<script>` tag that Shopify stores add to their theme
3. Floating chat bubble → expandable chat window
4. Golden Hour theme (CSS vars already defined in test_chat.html)

**Files to create:**
- `frontend/src/components/ChatWidget.tsx`
- `frontend/src/components/ProductCard.tsx`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/lib/api.ts`

### Priority 4: Redis Session Persistence
**Why:** Currently sessions are in-memory — lost on server restart.

**Approach:**
- Replace `_InMemoryContextManager` with `RedisContextManager`
- `ConversationContext.to_json()` / `from_json()` already work
- Set 1-hour TTL on session keys

**Files to modify:**
- `app/services/conversation_engine.py` — add `RedisContextManager` class
- `main.py` — initialize Redis connection in lifespan

### Priority 5: Store Owner Dashboard
**Why:** Store owners need to see conversations, analytics, escalations.

**Approach:**
- React admin panel at `/admin`
- Shows: active conversations, escalation alerts, conversion metrics
- Connect via REST API endpoints

---

## Important Notes for Next Session

### API Keys in .env
The `.env` file contains real Groq and Pinecone API keys. These work but should be rotated before any public deployment.

### Branding
The project was originally called "SunsetBot" (Sessions 1-2), briefly "VoixA" (Session 3 folder name), and the code internally uses "SunsetBot" everywhere. Stick with **SunsetBot** in code. The final customer-facing brand name can be decided later — it's just a string in StoreConfig.

### Mock vs Production Mode
ProductIntelligence auto-detects:
- **Mock mode:** No Pinecone key or index not found → uses 20 demo products with pre-computed embeddings
- **Pinecone mode:** Valid key + index exists → real vector search

ConversationEngine has the same pattern — if Groq key is missing, server starts in degraded mode.

### Test Coverage
There are no automated tests yet. The smoke test in `conversation_engine.py` (`if __name__ == "__main__"`) covers basic intent classification and response generation. Adding pytest tests should be a Session 5 priority.

### Deployment
Not deployed yet. Plan:
- Backend → Railway (or Fly.io)
- Frontend → Vercel
- Database → Supabase (PostgreSQL)
- Redis → Upstash
- Estimated monthly cost at launch: $20-50/mo

---

## Quick Reference: How Messages Flow

```
Browser (test_chat.html)
    │
    ▼ WebSocket JSON: {"message": "red dresses under $60"}
    │
main.py:websocket_chat()
    ├─ Rate limit check
    ├─ Send typing indicator
    │
    ▼
ConversationEngine.process_message()
    │
    ├─ 1. IntentClassifier.classify()        → "product_search"
    ├─ 2. EntityExtractor.extract()          → {colors: ["red"], max_price: 60, category: "dress"}
    ├─ 3. ProductIntelligence.search()       → [Product, Product, ...]
    ├─ 4. ResponseGenerator.generate()       → Groq API call → "Here are some red dresses..."
    ├─ 5. EscalationHandler.check()          → None (no escalation needed)
    ├─ 6. Update sentiment in context
    ├─ 7. Save to history
    │
    ▼ EngineResponse
    │
main.py:_serialize_engine_response()
    │
    ▼ WebSocket JSON: {"type": "message", "text": "...", "products": [...]}
    │
Browser renders response + product cards
```

---

## Commands Cheat Sheet

```bash
# Start server
cd ~/sunsetbot/backend && source venv/bin/activate && python main.py

# Health check
curl http://localhost:8000/health

# View Swagger docs
open http://localhost:8000/docs

# Test chat
open test_chat.html  # in browser

# Smoke test conversation engine
python app/services/conversation_engine.py

# Seed/test product intelligence
python app/services/product_intelligence.py

# Install new dependency
pip install <package> && pip freeze | grep <package> >> requirements.txt
```
