# Product Requirements Document (PRD)
## AI E-commerce Assistant for Shopify

**Version:** 1.0  
**Date:** February 14, 2026  
**Status:** Active Development  
**Project Codename:** Jerry The Customer Service Bot

---

## Executive Summary

### Product Vision
An AI-powered conversational commerce assistant that integrates seamlessly with Shopify stores to provide intelligent product recommendations, customer support, and sales automation—increasing conversion rates and average order value while reducing support costs.

### Target Market
- **Primary:** Shopify store owners with $10k-$500k/month revenue
- **Secondary:** E-commerce brands on other platforms (future expansion)
- **Market Size:** 4.4M+ active Shopify stores globally

### Value Proposition
"Turn every browser into a buyer with AI that knows your products better than your best salesperson."

### Success Metrics
- **Phase 1 (MVP - Week 2):** 1 working demo on test store
- **Phase 2 (Beta - Week 4):** 3 paying beta customers
- **Phase 3 (Growth - Week 8):** 10 customers, $2,000 MRR
- **6 months:** 50 customers, $10,000 MRR
- **12 months:** 200 customers, $40,000 MRR

---

## Product Overview

### What It Does
Jerry The Customer Service Bot is an AI assistant that embeds in Shopify stores to:

1. **Understand Products Deeply**
   - Ingests entire product catalog (titles, descriptions, variants, prices, inventory)
   - Creates semantic understanding using vector embeddings
   - Handles natural language queries ("red dresses under $50")

2. **Engage Customers Conversationally**
   - Answers pre-sale questions in real-time
   - Provides personalized recommendations
   - Assists with checkout process
   - Tracks orders and handles post-sale support

3. **Automate Sales Workflows**
   - Abandoned cart recovery
   - Cross-sell and upsell suggestions
   - Inventory-based urgency messaging
   - Customer satisfaction tracking

### What It Doesn't Do (V1 Scope)
- ❌ Replace human support entirely (escalates complex issues)
- ❌ Process refunds automatically (hands off to humans)
- ❌ Modify product prices or inventory (read-only initially)
- ❌ Handle multi-channel (just Shopify for now)

---

## User Personas

### Persona 1: Sarah - Growing Shopify Store Owner
**Demographics:**
- Age: 32
- Role: Owner/Operator
- Store: Fashion boutique, $30k/month revenue
- Team: Just her + 1 part-time VA

**Pain Points:**
- Spends 4+ hours/day answering repetitive questions
- Loses sales when she's offline
- Can't afford full-time customer service
- Struggles to upsell effectively

**Goals:**
- Automate FAQs (sizing, shipping, returns)
- Increase average order value
- Provide 24/7 support
- Focus on product sourcing, not support

**Success Criteria:**
- Saves 15+ hours/week
- Increases AOV by 20%+
- Improves conversion rate by 10%+

### Persona 2: Mike - Established E-commerce Brand
**Demographics:**
- Age: 45
- Role: CEO
- Store: Electronics/gadgets, $200k/month revenue
- Team: 5 full-time (operations, marketing, support)

**Pain Points:**
- Support team overwhelmed during product launches
- Inconsistent product knowledge across team
- Difficult to track what customers actually want
- Lost sales from slow response times

**Goals:**
- Scale support without hiring
- Provide consistent, accurate product info
- Capture customer intent data
- Reduce time to first response

**Success Criteria:**
- Handles 60%+ of tier-1 support
- 90%+ accuracy on product questions
- <30 second response time
- Detailed analytics on customer needs

---

## Core Features (MVP - Phase 1)

### Feature 1: Product Intelligence & Recommendations

#### 1.1 Product Catalog Ingestion
**User Story:** As a store owner, I want the bot to automatically learn about all my products so it can answer customer questions accurately.

**Functionality:**
- On app installation, pull all products via Shopify API
- Extract: title, description, variants, prices, images, inventory, tags
- Generate vector embeddings for semantic search
- Update catalog daily (scheduled job)
- Real-time updates via Shopify webhooks (products/create, update, delete)

**Technical Implementation:**
```python
# Data Flow
Shopify API → Python Backend → Sentence Transformer (embeddings) → Vector DB (Pinecone)

# Scheduled Update (runs daily at 2 AM store timezone)
def sync_product_catalog(store_id):
    products = shopify.Product.find()
    for product in products:
        embedding = model.encode(f"{product.title} {product.description}")
        vector_db.upsert(store_id, product.id, embedding, metadata={
            'title': product.title,
            'price': product.price,
            'variants': product.variants,
            'inventory': product.inventory_quantity
        })
```

**Acceptance Criteria:**
- ✅ Syncs 500+ products in <2 minutes
- ✅ Handles products with 10+ variants
- ✅ Updates within 5 minutes of product change
- ✅ Stores product images for chat display

#### 1.2 Natural Language Product Search
**User Story:** As a customer, I want to find products by describing what I want in plain English.

**Functionality:**
- Convert customer query to embedding
- Perform vector similarity search
- Apply filters (price, color, size, category)
- Rank by: relevance × inventory × popularity
- Return top 5 results with images

**Example Queries Handled:**
- "Show me red dresses under $50"
- "What's your best-selling winter jacket?"
- "Do you have waterproof hiking boots in size 10?"
- "Something similar to [product name] but cheaper"

**Technical Implementation:**
```python
def search_products(query, store_id, filters=None):
    # Embed query
    query_embedding = model.encode(query)
    
    # Vector search
    results = vector_db.query(
        store_id=store_id,
        embedding=query_embedding,
        top_k=20,
        filters=filters
    )
    
    # Re-rank by inventory and popularity
    ranked = rerank(results, weights={
        'similarity': 0.6,
        'inventory': 0.2,
        'sales_velocity': 0.2
    })
    
    return ranked[:5]
```

**Acceptance Criteria:**
- ✅ Returns relevant results in <500ms
- ✅ 85%+ accuracy on subjective queries
- ✅ Handles typos and synonyms
- ✅ Shows images + prices + variants

#### 1.3 Personalized Recommendations
**User Story:** As a customer, I want the bot to suggest products I'll actually like based on what I'm browsing.

**Functionality:**
- Track browsing history (viewed products)
- Analyze cart contents
- Generate recommendations:
  - **Similar items:** Vector similarity to viewed products
  - **Frequently bought together:** Order history analysis
  - **Upsells:** Higher-priced alternatives with better features
  - **Cross-sells:** Complementary products

**Recommendation Types:**

| Type | Trigger | Logic |
|------|---------|-------|
| Similar | Customer views product | Find nearest vectors |
| Complementary | Customer adds to cart | "Bought together" analysis |
| Upsell | Customer asks about product | Same category, higher price, better reviews |
| Downsell | Customer price-sensitive | Same category, lower price |

**Technical Implementation:**
```python
def generate_recommendations(customer_session, product_id, type='similar'):
    if type == 'similar':
        product_embedding = vector_db.get_embedding(product_id)
        similar = vector_db.query(embedding=product_embedding, top_k=5)
        return similar
    
    elif type == 'complementary':
        # Analyze order data
        frequently_bought = db.query(
            "SELECT product_b FROM order_items "
            "WHERE product_a = %s GROUP BY product_b "
            "ORDER BY COUNT(*) DESC LIMIT 3",
            product_id
        )
        return frequently_bought
    
    elif type == 'upsell':
        product = get_product(product_id)
        upsells = vector_db.query(
            filters={
                'category': product.category,
                'price_range': f"{product.price * 1.2}-{product.price * 2}"
            },
            top_k=3
        )
        return upsells
```

**Acceptance Criteria:**
- ✅ Recommendations have 40%+ click-through rate
- ✅ Upsells increase AOV by 15%+
- ✅ Shows 3-5 recommendations per interaction
- ✅ Updates based on browsing behavior

---

### Feature 2: Conversational Commerce & Customer Support

#### 2.1 AI Chat Interface
**User Story:** As a customer, I want to chat with the store in real-time and get instant answers.

**Functionality:**
- Embedded chat widget on all store pages
- Real-time messaging (WebSocket connection)
- Typing indicators and read receipts
- Image support (show product photos)
- Mobile-responsive design

**Chat Widget Appearance:**
- **Position:** Bottom-right corner
- **Theme:** Golden Hour (gradient orange-to-purple)
- **Trigger:** Auto-open after 30 seconds OR on exit intent
- **Minimized state:** Small bubble with notification badge

**Technical Implementation:**
```python
# FastAPI WebSocket endpoint
@app.websocket("/chat/{store_id}/{session_id}")
async def chat_endpoint(websocket: WebSocket, store_id: str, session_id: str):
    await websocket.accept()
    
    # Load conversation history
    history = get_conversation_history(session_id)
    
    while True:
        # Receive message
        message = await websocket.receive_text()
        
        # Generate response
        response = await generate_ai_response(
            message=message,
            history=history,
            store_id=store_id,
            session_id=session_id
        )
        
        # Send response
        await websocket.send_json({
            'type': 'message',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update history
        history.append({'role': 'user', 'content': message})
        history.append({'role': 'assistant', 'content': response})
```

**Acceptance Criteria:**
- ✅ Loads in <1 second
- ✅ Response time <2 seconds
- ✅ Works on mobile and desktop
- ✅ Persists conversation across page loads

#### 2.2 Context-Aware Conversations
**User Story:** As a customer, I want the bot to remember what we talked about without repeating myself.

**Functionality:**
- Maintain conversation history (last 20 messages)
- Track customer intent (browsing, purchasing, support)
- Remember mentioned products, preferences, issues
- Provide context to each AI response

**Context Types Tracked:**

| Context | Example | Storage |
|---------|---------|---------|
| Products viewed | Customer viewed "Red Dress #123" | Session cache |
| Cart contents | 2 items, total $89 | Shopify API |
| Previous questions | Asked about sizing | Conversation history |
| Customer data | Email, previous orders | PostgreSQL |
| Intent | "Buying" vs "Just browsing" | Session flag |

**Technical Implementation:**
```python
class ConversationContext:
    def __init__(self, session_id):
        self.session_id = session_id
        self.history = []
        self.viewed_products = []
        self.cart_items = []
        self.customer_id = None
        self.intent = 'browsing'
        self.sentiment = 'neutral'
    
    def add_message(self, role, content):
        self.history.append({'role': role, 'content': content})
        
        # Analyze intent
        if any(word in content.lower() for word in ['buy', 'purchase', 'checkout']):
            self.intent = 'purchasing'
        elif any(word in content.lower() for word in ['track', 'order', 'shipped']):
            self.intent = 'support'
    
    def get_context_prompt(self):
        return f"""
        Conversation History: {self.history[-10:]}
        Products Viewed: {self.viewed_products}
        Cart Items: {self.cart_items}
        Customer Intent: {self.intent}
        """
```

**Acceptance Criteria:**
- ✅ Remembers products mentioned 5+ messages ago
- ✅ Doesn't repeat information already provided
- ✅ Correctly identifies intent (buy vs browse vs support)
- ✅ Maintains context across sessions (if logged in)

#### 2.3 Full Customer Journey Support
**User Story:** As a customer, I want help at every stage—from browsing to post-purchase.

**Supported Journey Stages:**

**Pre-Sale (Discovery & Consideration):**
- Product search and recommendations
- Feature comparisons
- Sizing and fit advice
- Shipping and return policies
- Availability checks

**During Sale (Checkout):**
- Add to cart assistance
- Discount code application
- Payment troubleshooting
- Guest checkout guidance

**Post-Sale (Fulfillment & Support):**
- Order status tracking
- Shipping updates
- Return/exchange requests
- Product care instructions
- Warranty questions

**Example Conversation Flows:**

```
FLOW 1: Product Discovery
Customer: "I need a waterproof jacket for hiking"
Bot: "Great! I found 3 waterproof jackets perfect for hiking:
      1. Alpine Pro Jacket ($129) - Rated 4.8⭐
      2. TrailBlazer Weatherproof ($89) - Best seller
      3. Summit Shield ($199) - Premium option
      Which features matter most to you?"

Customer: "I want something breathable, under $150"
Bot: "The Alpine Pro Jacket ($129) is perfect! It has:
      ✓ Waterproof rating: 10,000mm
      ✓ Breathable mesh lining
      ✓ Lightweight (only 12oz)
      ✓ In stock in sizes S-XL
      Want to add it to your cart?"

FLOW 2: Order Tracking
Customer: "Where is my order?"
Bot: [Looks up recent orders via Shopify API]
     "Your order #12345 shipped on Feb 12!
      📦 Status: Out for delivery
      📍 Expected: Today by 8pm
      🔗 Track here: [USPS link]
      Anything else I can help with?"
```

**Acceptance Criteria:**
- ✅ Handles 15+ common question types
- ✅ Provides order tracking automatically
- ✅ Can add items to cart via chat
- ✅ Shares relevant policy links

#### 2.4 Intelligent Escalation
**User Story:** As a store owner, I want the bot to escalate complex issues to me automatically.

**Escalation Triggers:**

| Condition | Action | Priority |
|-----------|--------|----------|
| Sentiment = angry/frustrated | Escalate immediately | High |
| Refund request >$100 | Escalate with context | High |
| 3+ failed responses in a row | Offer human support | Medium |
| Technical issue (payment failed) | Escalate with error logs | High |
| VIP customer (LTV >$1000) | Notify store owner | Medium |
| Question outside knowledge base | Escalate or say "I don't know" | Low |

**Technical Implementation:**
```python
def check_escalation(context, message, response_confidence):
    # Sentiment analysis
    sentiment = analyze_sentiment(message)
    if sentiment['score'] < -0.5:  # Negative sentiment
        return escalate(reason='negative_sentiment', priority='high')
    
    # Confidence check
    if response_confidence < 0.7:
        return escalate(reason='low_confidence', priority='low')
    
    # Keyword triggers
    escalation_keywords = ['refund', 'manager', 'complaint', 'lawyer']
    if any(word in message.lower() for word in escalation_keywords):
        return escalate(reason='keyword_trigger', priority='high')
    
    # VIP customer
    if context.customer_ltv > 1000:
        notify_owner(message=f"VIP customer {context.customer_id} needs help")
    
    return None  # No escalation needed
```

**Escalation Flow:**
1. Bot detects escalation trigger
2. Shows message: "Let me connect you with a team member who can help better with this."
3. Sends notification to store owner (email + SMS if high priority)
4. Provides full conversation context
5. Store owner can respond via admin dashboard

**Acceptance Criteria:**
- ✅ Escalates within 10 seconds of trigger
- ✅ Includes full conversation history
- ✅ <5% false positive escalations
- ✅ Store owner gets mobile notification

---

### Feature 3: Data Integration & Automation

#### 3.1 Shopify API Integration
**User Story:** As a store owner, I want the bot to stay in sync with my store automatically.

**API Endpoints Used:**

| Endpoint | Purpose | Frequency |
|----------|---------|-----------|
| `/admin/api/products.json` | Fetch product catalog | Daily sync |
| `/admin/api/orders.json` | Track orders for customers | On-demand |
| `/admin/api/customers.json` | Get customer data | On-demand |
| `/admin/api/inventory_levels.json` | Check stock levels | Real-time |
| `/admin/api/webhooks.json` | Register event listeners | On install |

**Webhook Subscriptions:**

```python
WEBHOOKS = [
    'products/create',    # New product added → Update vector DB
    'products/update',    # Product changed → Refresh embeddings
    'products/delete',    # Product removed → Delete from DB
    'orders/create',      # New order → Update "bought together" data
    'inventory_levels/update',  # Stock changed → Update availability
]
```

**Authentication Flow:**
1. Store owner clicks "Add App" on Shopify App Store
2. Redirected to our OAuth consent page
3. Grants permissions: `read_products`, `read_orders`, `read_customers`
4. We receive access token (stored encrypted in PostgreSQL)
5. Register webhooks for real-time updates

**Technical Implementation:**
```python
# OAuth callback
@app.get('/auth/callback')
async def shopify_callback(shop: str, code: str):
    # Exchange code for access token
    access_token = shopify.exchange_code(shop, code)
    
    # Store credentials
    db.stores.insert({
        'shop_domain': shop,
        'access_token': encrypt(access_token),
        'installed_at': datetime.now()
    })
    
    # Register webhooks
    for topic in WEBHOOKS:
        shopify.Webhook.create({
            'topic': topic,
            'address': f'https://api.sunsetbot.ai/webhooks/{topic}',
            'format': 'json'
        })
    
    # Initial product sync
    await sync_product_catalog(shop)
    
    return redirect(f'https://{shop}/admin/apps/sunsetbot')
```

**Acceptance Criteria:**
- ✅ OAuth flow completes in <30 seconds
- ✅ Webhooks fire within 5 seconds of events
- ✅ Handles API rate limits gracefully
- ✅ Supports multiple stores (multi-tenant)

#### 3.2 Abandoned Cart Recovery
**User Story:** As a store owner, I want to automatically re-engage customers who abandon their carts.

**Functionality:**
- Detect abandoned carts (webhook: `checkouts/create`)
- Wait 1 hour (customer may return naturally)
- If still not purchased:
  - Send email with bot link
  - Offer 10% discount code
  - Remind of items in cart
- Track recovery rate

**Recovery Email Template:**
```html
Subject: You left something behind! 🛒

Hi [Name],

You were looking at:
- [Product 1 - Image]
- [Product 2 - Image]

Come back and complete your order—I'm here to help!
Plus, use code COMEBACK10 for 10% off.

[Chat with me now] → Opens chat widget with cart pre-loaded

- Jerry The Customer Service Bot 🌅
```

**Technical Implementation:**
```python
# Webhook handler
@app.post('/webhooks/checkouts/create')
async def abandoned_cart_webhook(payload):
    checkout_id = payload['id']
    customer_email = payload['email']
    cart_items = payload['line_items']
    
    # Schedule recovery email (1 hour delay)
    await schedule_task(
        task='send_cart_recovery_email',
        delay_seconds=3600,
        params={
            'checkout_id': checkout_id,
            'email': customer_email,
            'items': cart_items
        }
    )

# Scheduled task (runs after 1 hour)
async def send_cart_recovery_email(checkout_id, email, items):
    # Check if order completed
    if order_exists(checkout_id):
        return  # Customer already purchased
    
    # Generate discount code
    discount_code = shopify.DiscountCode.create({
        'code': 'COMEBACK10',
        'value_type': 'percentage',
        'value': 10,
        'applies_to': 'checkout'
    })
    
    # Send email
    await send_email(
        to=email,
        template='cart_recovery',
        data={'items': items, 'code': discount_code}
    )
    
    # Log analytics
    db.analytics.insert({
        'event': 'cart_recovery_sent',
        'checkout_id': checkout_id
    })
```

**Acceptance Criteria:**
- ✅ Sends within 1 hour of abandonment
- ✅ Doesn't send if order already completed
- ✅ Tracks open rate and recovery rate
- ✅ 20%+ recovery rate target

#### 3.3 Analytics Dashboard
**User Story:** As a store owner, I want to see how the bot is performing and where it's helping most.

**Key Metrics Displayed:**

**Engagement Metrics:**
- Conversations started (daily, weekly, monthly)
- Average conversation length
- Repeat conversation rate
- Peak usage times

**Conversion Metrics:**
- Conversation → Purchase rate
- Average order value (with bot vs without)
- Products recommended → added to cart
- Cart recovery success rate

**Support Metrics:**
- Questions answered automatically
- Escalations to human support
- Customer satisfaction score (thumbs up/down)
- Average response time

**Product Performance:**
- Most recommended products
- Highest converting products
- Products with most questions

**Dashboard Layout (React):**
```
┌─────────────────────────────────────────────────┐
│  Jerry The Customer Service Bot Analytics - Last 30 Days             │
├─────────────────────────────────────────────────┤
│  📊 Overview                                    │
│  ├─ 1,247 Conversations (+23% vs last month)   │
│  ├─ $12,450 Revenue attributed to bot           │
│  ├─ 18.3% Conversion rate                       │
│  └─ 4.7⭐ Average satisfaction                  │
├─────────────────────────────────────────────────┤
│  📈 Conversion Funnel                           │
│  [Chart: Conversations → Recommendations →      │
│           Add to Cart → Purchase]               │
├─────────────────────────────────────────────────┤
│  🏆 Top Performing Products                     │
│  1. Red Summer Dress - 89 recommendations       │
│  2. Leather Wallet - 67 recommendations         │
│  3. Hiking Boots - 54 recommendations           │
├─────────────────────────────────────────────────┤
│  💬 Recent Conversations (click to view)        │
│  └─ Customer asked about sizing...              │
└─────────────────────────────────────────────────┘
```

**Technical Implementation:**
```python
# Analytics tracking
class AnalyticsTracker:
    def track_event(self, store_id, event_type, metadata):
        db.analytics.insert({
            'store_id': store_id,
            'event_type': event_type,
            'metadata': json.dumps(metadata),
            'timestamp': datetime.now()
        })
    
    def get_dashboard_stats(self, store_id, days=30):
        start_date = datetime.now() - timedelta(days=days)
        
        # Conversation stats
        conversations = db.analytics.count(
            store_id=store_id,
            event_type='conversation_started',
            timestamp__gte=start_date
        )
        
        # Conversion stats
        purchases = db.analytics.count(
            store_id=store_id,
            event_type='purchase_attributed',
            timestamp__gte=start_date
        )
        
        revenue = db.analytics.sum(
            store_id=store_id,
            event_type='purchase_attributed',
            field='metadata.order_value',
            timestamp__gte=start_date
        )
        
        return {
            'conversations': conversations,
            'purchases': purchases,
            'revenue': revenue,
            'conversion_rate': (purchases / conversations) * 100
        }
```

**Acceptance Criteria:**
- ✅ Dashboard loads in <2 seconds
- ✅ Real-time updates (refreshes every 30 seconds)
- ✅ Export data as CSV
- ✅ Filter by date range

#### 3.4 Inventory-Based Messaging
**User Story:** As a store owner, I want the bot to create urgency when stock is low.

**Functionality:**
- Track inventory levels via Shopify API
- Show urgency messages when stock <10 units
- Prevent recommendations for out-of-stock items
- Offer alternatives when product unavailable

**Urgency Messages:**

| Stock Level | Message |
|-------------|---------|
| 0 units | "Sorry, this is out of stock! Would you like me to find something similar?" |
| 1-3 units | "Only [X] left in stock—order soon!" |
| 4-10 units | "Low stock—[X] available" |
| 10+ units | "In stock and ready to ship!" |

**Technical Implementation:**
```python
def get_inventory_message(product_id):
    inventory = shopify.InventoryLevel.find(product_id)
    quantity = inventory.available
    
    if quantity == 0:
        return {
            'available': False,
            'message': "Sorry, this is out of stock!",
            'action': 'suggest_alternative'
        }
    elif quantity <= 3:
        return {
            'available': True,
            'message': f"⚡ Only {quantity} left—order soon!",
            'urgency': 'high'
        }
    elif quantity <= 10:
        return {
            'available': True,
            'message': f"Low stock—{quantity} available",
            'urgency': 'medium'
        }
    else:
        return {
            'available': True,
            'message': "In stock and ready to ship!",
            'urgency': 'low'
        }
```

**Acceptance Criteria:**
- ✅ Inventory updates in real-time
- ✅ Never recommends out-of-stock items
- ✅ Suggests alternatives automatically
- ✅ Urgency messages increase conversion by 10%+

---

## Technical Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOMER FACING                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Shopify Store (customer's browser)                  │   │
│  │  ├─ Embedded Chat Widget (React)                     │   │
│  │  └─ WebSocket connection to backend                  │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS / WSS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  React App (Vercel)                                  │   │
│  │  ├─ Customer chat interface                          │   │
│  │  ├─ Store owner admin dashboard                      │   │
│  │  └─ Analytics visualization                          │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ REST API / WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND LAYER                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Server (Railway/Render - Python 3.11)       │   │
│  │                                                       │   │
│  │  API Routes:                                         │   │
│  │  ├─ /chat (WebSocket) - Real-time messaging         │   │
│  │  ├─ /api/products - Product search                  │   │
│  │  ├─ /api/recommendations - AI suggestions           │   │
│  │  ├─ /api/analytics - Dashboard data                 │   │
│  │  ├─ /webhooks/* - Shopify event handlers            │   │
│  │  └─ /auth/* - OAuth flow                            │   │
│  │                                                       │   │
│  │  Core Services:                                      │   │
│  │  ├─ ConversationEngine (AI logic)                   │   │
│  │  ├─ ProductIntelligence (recommendations)           │   │
│  │  ├─ ShopifyIntegration (API wrapper)                │   │
│  │  ├─ AnalyticsService (tracking)                     │   │
│  │  └─ EscalationHandler (human handoff)               │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────┬───────────────────┬──────────────┬─────────────┘
             │                   │              │
             ▼                   ▼              ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐
│  AI LAYER        │  │  DATA LAYER     │  │  EXTERNAL    │
│                  │  │                 │  │  APIS        │
│  Groq API        │  │  PostgreSQL     │  │              │
│  (Llama 3.1 70B) │  │  - Stores       │  │  Shopify     │
│                  │  │  - Customers    │  │  Admin API   │
│  Sentence        │  │  - Convos       │  │              │
│  Transformers    │  │  - Analytics    │  │  Email       │
│  (embeddings)    │  │                 │  │  Provider    │
│                  │  │  Redis          │  │  (SendGrid)  │
│  RoBERTa         │  │  - Sessions     │  │              │
│  (sentiment)     │  │  - Cache        │  │  SMS         │
│                  │  │  - Rate limits  │  │  (Twilio)    │
│  Pinecone        │  │                 │  │              │
│  (vector DB)     │  │  Vector DB      │  └──────────────┘
│  - Product       │  │  (Pinecone)     │
│    embeddings    │  │  - Product      │
│                  │  │    embeddings   │
└──────────────────┘  └─────────────────┘
```

### Tech Stack Details

#### Frontend
- **Framework:** React 19.2 + TypeScript
- **Build Tool:** Vite 7.2
- **UI Library:** shadcn/ui (Radix UI primitives)
- **Styling:** Tailwind CSS (Golden Hour theme)
- **State Management:** React Context + hooks
- **WebSocket:** Native WebSocket API
- **Charts:** Recharts
- **Deployment:** Vercel (free tier)

#### Backend
- **Framework:** FastAPI 0.110+ (Python 3.11)
- **ASGI Server:** Uvicorn
- **WebSocket:** FastAPI WebSocket support
- **Task Queue:** Celery + Redis (for scheduled tasks)
- **Authentication:** JWT tokens
- **API Client:** httpx (async HTTP)
- **Deployment:** Railway.app ($5-20/month)

#### AI/ML
- **LLM:** Llama 3.1 70B via Groq API
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Sentiment:** transformers (RoBERTa)
- **Vector Search:** Pinecone (free tier: 1M vectors)

#### Data Storage
- **Primary DB:** PostgreSQL (Supabase free tier)
- **Cache:** Redis (Upstash free tier)
- **Vector DB:** Pinecone (managed service)

#### External APIs
- **E-commerce:** Shopify Admin API
- **Email:** SendGrid (free tier: 100 emails/day)
- **SMS:** Twilio (pay-as-you-go, optional)

---

## Data Models

### Store
```python
class Store:
    id: UUID
    shop_domain: str  # e.g., "mystore.myshopify.com"
    access_token: str  # Encrypted Shopify API token
    owner_email: str
    plan: str  # 'starter' | 'growth' | 'pro' | 'enterprise'
    monthly_conversation_limit: int
    installed_at: datetime
    active: bool
    settings: JSON  # Store-specific config
```

### Product
```python
class Product:
    id: UUID
    store_id: UUID  # Foreign key
    shopify_product_id: str
    title: str
    description: str
    price: Decimal
    compare_at_price: Decimal | None
    variants: List[ProductVariant]
    images: List[str]  # URLs
    tags: List[str]
    category: str
    inventory_quantity: int
    embedding: List[float]  # 384-dim vector
    last_synced: datetime
```

### Conversation
```python
class Conversation:
    id: UUID
    store_id: UUID
    session_id: str
    customer_id: str | None  # Shopify customer ID if known
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    resulted_in_purchase: bool
    order_id: str | None
    customer_satisfaction: int | None  # 1-5 stars
    escalated: bool
    escalation_reason: str | None
```

### Message
```python
class Message:
    id: UUID
    conversation_id: UUID
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    timestamp: datetime
    metadata: JSON  # Product IDs mentioned, intent, sentiment
```

### AnalyticsEvent
```python
class AnalyticsEvent:
    id: UUID
    store_id: UUID
    event_type: str  # 'conversation_started', 'product_recommended', etc.
    metadata: JSON
    timestamp: datetime
```

---

## API Endpoints

### Public API (Customer-facing)

#### `POST /api/chat/message`
Send a message to the AI assistant.

**Request:**
```json
{
  "store_id": "uuid",
  "session_id": "string",
  "message": "Do you have red dresses?",
  "context": {
    "page_url": "https://store.com/collections/dresses",
    "cart_items": ["product_id_1"]
  }
}
```

**Response:**
```json
{
  "response": "Yes! I found 5 red dresses for you...",
  "products": [
    {
      "id": "product_id",
      "title": "Red Summer Dress",
      "price": "$49.99",
      "image": "https://...",
      "url": "https://store.com/products/red-summer-dress"
    }
  ],
  "suggested_actions": ["view_product", "add_to_cart"],
  "confidence": 0.92
}
```

#### `WebSocket /ws/chat/{store_id}/{session_id}`
Real-time chat connection.

**Message Types:**
```json
// Customer message
{
  "type": "message",
  "content": "Show me boots"
}

// AI response
{
  "type": "response",
  "content": "Here are our top hiking boots...",
  "products": [...],
  "typing": false
}

// Typing indicator
{
  "type": "typing",
  "is_typing": true
}
```

### Admin API (Store owner-facing)

#### `GET /api/dashboard/stats`
Get dashboard analytics.

**Query Params:**
- `store_id`: UUID
- `start_date`: ISO date
- `end_date`: ISO date

**Response:**
```json
{
  "conversations": 1247,
  "conversion_rate": 18.3,
  "revenue_attributed": 12450.00,
  "top_products": [
    {"product_id": "123", "recommendations": 89}
  ],
  "satisfaction_avg": 4.7
}
```

#### `GET /api/conversations`
List recent conversations.

**Response:**
```json
{
  "conversations": [
    {
      "id": "uuid",
      "started_at": "2026-02-14T10:30:00Z",
      "message_count": 12,
      "resulted_in_purchase": true,
      "order_value": 89.99
    }
  ]
}
```

### Webhook Endpoints

#### `POST /webhooks/products/create`
Handle new product creation.

#### `POST /webhooks/products/update`
Handle product updates.

#### `POST /webhooks/checkouts/create`
Handle abandoned carts.

---

## AI Prompt Engineering

### System Prompt Template
```python
SYSTEM_PROMPT = """
You are an AI shopping assistant for {store_name}, an e-commerce store selling {product_category}.

Your role is to:
1. Help customers find products they'll love
2. Answer questions about products, shipping, and policies
3. Provide personalized recommendations
4. Be friendly, helpful, and concise

Current context:
- Customer is viewing: {current_page}
- Cart contents: {cart_items}
- Previous conversation: {conversation_summary}

Product catalog knowledge:
{product_catalog_summary}

Store policies:
- Shipping: {shipping_policy}
- Returns: {return_policy}
- Payment: {payment_methods}

Guidelines:
- Keep responses under 3 sentences unless asked for details
- Always show product images when recommending
- If unsure, say "Let me check with the team" instead of guessing
- Use emojis sparingly (1-2 per message max)
- Focus on benefits, not just features
- Create urgency gently (e.g., "popular item" not "buy now!")

If the customer is frustrated or wants a refund >$100, escalate to human support.
"""
```

### Conversation Flow Templates

**Product Recommendation:**
```python
RECOMMENDATION_TEMPLATE = """
Based on your interest in {trigger_product}, I found {num_recommendations} similar items you might love:

{for product in recommendations:}
{product.emoji} {product.title}
   ${product.price} | {product.rating}⭐
   {product.key_feature}
   [View product]

{end for}

Which one catches your eye?
"""
```

**Order Tracking:**
```python
ORDER_TRACKING_TEMPLATE = """
📦 Your order #{order_number} is {status}!

{if status == 'shipped':}
Expected delivery: {delivery_date}
Track here: {tracking_url}
{elif status == 'processing':}
We're preparing your order now. Ships within 1-2 business days.
{elif status == 'delivered':}
Delivered on {delivery_date}! Hope you love it 💚
{end if}

Need anything else?
"""
```

---

## Success Metrics & KPIs

### Phase 1: MVP (Week 2)
- ✅ Bot responds to queries in <2 seconds
- ✅ 80%+ accuracy on product questions
- ✅ Works on 1 test Shopify store
- ✅ Logs all conversations

### Phase 2: Beta (Week 4)
- ✅ 3 paying beta customers
- ✅ 50+ conversations handled
- ✅ 15%+ conversation → purchase rate
- ✅ 4.0+ star satisfaction rating

### Phase 3: Growth (Week 8)
- ✅ 10 paying customers
- ✅ $2,000 MRR
- ✅ 500+ conversations/month
- ✅ 20%+ conversion rate
- ✅ 4.5+ star rating

### Long-term (6 months)
- ✅ 50 customers
- ✅ $10,000 MRR
- ✅ 90%+ uptime
- ✅ <1% churn rate
- ✅ Featured on Shopify App Store

---

## Risk Mitigation

### Technical Risks

**Risk 1: AI Quality Issues**
- **Impact:** Customers get wrong product recommendations
- **Likelihood:** Medium
- **Mitigation:**
  - Extensive testing before launch
  - Confidence thresholds (don't answer if <70% sure)
  - Human review of flagged conversations
  - A/B test against GPT-4 baseline

**Risk 2: Shopify API Rate Limits**
- **Impact:** Bot stops working during high traffic
- **Likelihood:** Low (we cache heavily)
- **Mitigation:**
  - Redis caching (60-second cache for product data)
  - Batch API requests
  - Queue system for non-urgent operations
  - Monitor rate limit headers

**Risk 3: Groq API Downtime**
- **Impact:** Bot can't respond to customers
- **Likelihood:** Low (99.9% uptime SLA)
- **Mitigation:**
  - Fallback to OpenAI API if Groq down
  - Queue messages during outages
  - Show "temporarily unavailable" message
  - Alert store owner

### Business Risks

**Risk 1: Low Conversion (Customers don't buy)**
- **Impact:** Can't prove ROI, high churn
- **Likelihood:** Medium
- **Mitigation:**
  - Offer 14-day free trial (prove value first)
  - Detailed analytics showing revenue attributed
  - Case studies from beta customers
  - Money-back guarantee if no improvement

**Risk 2: Shopify Changes API**
- **Impact:** App breaks, customer churn
- **Likelihood:** Low (API is stable)
- **Mitigation:**
  - Monitor Shopify developer blog
  - Use API versioning
  - Automated tests against API
  - Maintain backward compatibility

**Risk 3: Competition**
- **Impact:** Customers choose competitor
- **Likelihood:** High (many AI chatbots exist)
- **Mitigation:**
  - Niche down (best for Shopify, not generic)
  - Better product intelligence (our differentiator)
  - Superior UX (Golden Hour theme, fast responses)
  - Competitive pricing ($199 vs $299+ competitors)

---

## Go-to-Market Strategy

### Phase 1: Beta Launch (Weeks 1-4)
**Goal:** Get 3 paying beta customers

**Tactics:**
1. **Direct outreach** to Shopify stores ($10-50k/month revenue)
   - Offer: Free for 3 months + personalized setup
   - Ask: Testimonial + feedback
2. **Shopify Partners community**
   - Post in forums
   - Offer free implementation to agencies
3. **LinkedIn content**
   - Share build journey ("Building in public")
   - Tag Shopify store owners

**Budget:** $0
**Time:** 10 hours/week

### Phase 2: App Store Launch (Weeks 5-8)
**Goal:** Get 10 paying customers from organic traffic

**Tactics:**
1. **Shopify App Store listing**
   - Optimize title/description for search
   - Professional screenshots + demo video
   - Encourage reviews from beta customers
2. **Content marketing**
   - Blog: "How AI Chatbots Increase Shopify Sales"
   - Guest posts on Shopify blogs
   - YouTube tutorials
3. **Paid ads** (if budget allows)
   - Facebook ads targeting Shopify store owners
   - Budget: $500/month
   - Target: $50 CAC

**Budget:** $500-1000
**Time:** 20 hours/week

### Phase 3: Scale (Months 3-6)
**Goal:** 50 customers, $10k MRR

**Tactics:**
1. **Partnerships** with Shopify agencies
   - Revenue share (20% commission)
   - White-label option for agencies
2. **Affiliate program**
   - Pay $50 per customer referred
   - Recruit Shopify influencers
3. **SEO content**
   - Rank for "Shopify AI assistant"
   - Comparison pages (vs. competitors)

**Budget:** $2000-5000/month
**Time:** Full-time

---

## Pricing Strategy

### Tier Structure

| Tier | Price/mo | Conversations | Target Customer | Estimated Customers |
|------|----------|---------------|-----------------|---------------------|
| **Starter** | $99 | 500 | <$10k/mo stores | 60% |
| **Growth** | $199 | 2,000 | $10-50k/mo stores | 30% |
| **Pro** | $399 | 10,000 | $50k+/mo stores | 8% |
| **Enterprise** | Custom | Unlimited | $500k+/mo stores | 2% |

### Revenue Projections

**Month 3 (10 customers):**
- 6 × Starter ($99) = $594
- 3 × Growth ($199) = $597
- 1 × Pro ($399) = $399
- **Total: $1,590 MRR**

**Month 6 (50 customers):**
- 30 × Starter = $2,970
- 15 × Growth = $2,985
- 4 × Pro = $1,596
- 1 × Enterprise ($1000) = $1,000
- **Total: $8,551 MRR**

**Month 12 (200 customers):**
- 120 × Starter = $11,880
- 60 × Growth = $11,940
- 16 × Pro = $6,384
- 4 × Enterprise = $4,000
- **Total: $34,204 MRR**

### Cost Structure (at 200 customers)

| Cost | Amount/mo | Notes |
|------|-----------|-------|
| Hosting (Railway) | $50 | Scales with usage |
| Database (Supabase) | $25 | 100GB storage |
| Vector DB (Pinecone) | $70 | 5M vectors |
| Groq API | $0 | Free tier covers it |
| Email (SendGrid) | $20 | 40k emails |
| **Total Costs** | **$165** | |
| **Revenue** | **$34,204** | |
| **Profit** | **$34,039** | **99.5% margin** |

---

## Development Roadmap

### Week 1: Foundation
- [ ] Set up FastAPI backend structure
- [ ] Configure Groq API integration
- [ ] Build basic chat endpoint (REST + WebSocket)
- [ ] Set up PostgreSQL database
- [ ] Create React chat widget (basic UI)

### Week 2: Core AI
- [ ] Implement conversation engine
- [ ] Integrate Shopify API (OAuth flow)
- [ ] Build product catalog sync
- [ ] Add vector embeddings (Pinecone)
- [ ] Create recommendation logic
- [ ] **MILESTONE: Working demo on test store**

### Week 3: Beta Features
- [ ] Multi-tenant architecture
- [ ] Admin dashboard (React)
- [ ] Analytics tracking
- [ ] Abandoned cart recovery
- [ ] Stripe billing integration

### Week 4: Polish & Launch
- [ ] Improve UI/UX (Golden Hour theme refinement)
- [ ] Add escalation logic
- [ ] Write documentation
- [ ] Create marketing materials (screenshots, video)
- [ ] **MILESTONE: Shopify App Store listing live**

### Week 5-8: Growth Features
- [ ] Advanced recommendations (upsell/cross-sell)
- [ ] Sentiment analysis
- [ ] Email integration
- [ ] Performance optimizations
- [ ] A/B testing framework

### Months 3-6: Scale
- [ ] Multi-language support
- [ ] Voice commerce (optional)
- [ ] Mobile app (store owner admin)
- [ ] API for custom integrations
- [ ] White-label option

---

## Documentation Requirements

### For Future AI Handoff

**1. Architecture Documentation**
- System architecture diagram (Mermaid format)
- Data flow diagrams
- Database schema with relationships
- API endpoint specifications (OpenAPI/Swagger)

**2. Setup Guide**
- Local development environment setup
- Environment variables reference
- Database migrations
- Testing procedures

**3. Code Documentation**
- Inline comments for complex logic
- Function docstrings (Google style)
- README files in each major directory
- Code examples for common tasks

**4. Deployment Guide**
- Production deployment checklist
- Environment configuration
- Monitoring and logging setup
- Backup and disaster recovery

**5. User Guides**
- Store owner onboarding
- Admin dashboard tutorials
- Troubleshooting common issues
- FAQ

---

## Appendix

### Glossary

**AOV:** Average Order Value - average amount spent per order  
**CAC:** Customer Acquisition Cost - cost to acquire one paying customer  
**Churn:** Rate at which customers cancel their subscription  
**Embedding:** Vector representation of text for similarity search  
**Escalation:** Transferring conversation from bot to human  
**LLM:** Large Language Model (e.g., Llama 3, GPT-4)  
**MRR:** Monthly Recurring Revenue  
**RAG:** Retrieval-Augmented Generation - using external data with LLM  
**Vector DB:** Database optimized for similarity search using embeddings  
**Webhook:** HTTP callback triggered by events in external system  

### References

**Technical:**
- Shopify Admin API: https://shopify.dev/docs/api/admin
- Groq API Docs: https://groq.com/docs
- FastAPI Documentation: https://fastapi.tiangolo.com
- Pinecone Guides: https://docs.pinecone.io

**Business:**
- Shopify App Store Guidelines: https://shopify.dev/docs/apps/store
- SaaS Pricing Strategies: https://www.priceintelligently.com
- E-commerce Conversion Benchmarks: https://baymard.com

---

**END OF PRODUCT REQUIREMENTS DOCUMENT**

*This document will be updated as the product evolves. All changes should be documented in git commit messages.*
