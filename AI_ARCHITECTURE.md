# AI Architecture Document
## SunsetBot - E-commerce AI Assistant

**Version:** 1.0  
**Date:** February 14, 2026  
**Author:** Technical Architecture Team

---

## Table of Contents

1. [Overview](#overview)
2. [AI System Components](#ai-system-components)
3. [Conversation Engine](#conversation-engine)
4. [Product Intelligence System](#product-intelligence-system)
5. [Recommendation Engine](#recommendation-engine)
6. [Context Management](#context-management)
7. [Escalation Logic](#escalation-logic)
8. [Performance & Scaling](#performance--scaling)
9. [Monitoring & Observability](#monitoring--observability)

---

## Overview

### Architecture Philosophy

The AI architecture is designed with three core principles:

1. **Speed:** Responses in <2 seconds (customer expectation)
2. **Accuracy:** 85%+ correct product recommendations
3. **Scalability:** Support 1000+ concurrent conversations

### High-Level AI Flow

```
Customer Message
      ↓
[1] Intent Classification ← What does customer want?
      ↓
[2] Context Retrieval ← What do we know about them?
      ↓
[3] Product Search (if needed) ← Query vector DB
      ↓
[4] LLM Generation ← Craft response with Llama 3
      ↓
[5] Response Validation ← Check quality/safety
      ↓
[6] Analytics Logging ← Track for learning
      ↓
Response to Customer
```

---

## AI System Components

### Component Map

```
┌─────────────────────────────────────────────────────┐
│                  CONVERSATION ENGINE                │
│  Orchestrates entire AI flow                        │
│  ├─ Intent Classifier                               │
│  ├─ Context Manager                                 │
│  ├─ Response Generator                              │
│  └─ Quality Validator                               │
└────────────┬────────────────────────────────────────┘
             │
             ├─────────────────────────────────────────┐
             │                                         │
             ▼                                         ▼
┌──────────────────────────┐           ┌──────────────────────────┐
│  PRODUCT INTELLIGENCE    │           │  RECOMMENDATION ENGINE   │
│                          │           │                          │
│  ├─ Catalog Sync         │           │  ├─ Similarity Search    │
│  ├─ Embedding Generator  │           │  ├─ Collaborative Filter │
│  ├─ Vector Search        │           │  ├─ Rule Engine          │
│  └─ Inventory Tracker    │           │  └─ Ranking System       │
└──────────────────────────┘           └──────────────────────────┘
             │                                         │
             └─────────────┬───────────────────────────┘
                           │
                           ▼
             ┌──────────────────────────┐
             │  GROQ API (Llama 3.1)    │
             │  - Text generation       │
             │  - Conversation          │
             │  - Summarization         │
             └──────────────────────────┘
```

### Technology Choices & Rationale

| Component | Technology | Why This Choice? |
|-----------|-----------|------------------|
| **LLM** | Llama 3.1 70B via Groq | Free, fast (800 tokens/sec), good quality |
| **Embeddings** | all-MiniLM-L6-v2 | Fast, 384-dim, perfect for product search |
| **Vector DB** | Pinecone | Managed, 1M vectors free, <50ms latency |
| **Sentiment** | RoBERTa (cardiffnlp) | State-of-the-art, fine-tuned for social media |
| **Caching** | Redis | Sub-millisecond reads, perfect for sessions |

---

## Conversation Engine

### Core Responsibility
Manages the entire conversation lifecycle from message receipt to response delivery.

### Detailed Flow

```python
class ConversationEngine:
    """
    Orchestrates AI conversation flow.
    
    This is the main entry point for all customer messages.
    It coordinates between multiple AI components to generate
    contextually-appropriate, accurate responses.
    """
    
    async def process_message(self, message: str, context: ConversationContext) -> Response:
        """
        Main processing pipeline for customer messages.
        
        Flow:
        1. Classify intent (what does customer want?)
        2. Retrieve relevant context (conversation history, cart, etc.)
        3. Perform entity extraction (products, prices, sizes mentioned)
        4. Generate response using LLM
        5. Validate and enhance response
        6. Log analytics
        
        Args:
            message: Raw customer message
            context: Conversation context (history, customer data, etc.)
            
        Returns:
            Response object with text, products, suggested actions
        """
        
        # Step 1: Intent Classification
        intent = await self.classify_intent(message, context)
        # Returns: 'product_search' | 'support' | 'order_tracking' | 'general'
        
        # Step 2: Entity Extraction
        entities = await self.extract_entities(message)
        # Returns: {'products': [...], 'price_range': (min, max), 'colors': [...]}
        
        # Step 3: Context Augmentation
        augmented_context = await self.build_context(context, entities, intent)
        # Adds: relevant products, policies, customer history
        
        # Step 4: Check if we need product search
        products = []
        if intent == 'product_search':
            products = await self.product_intelligence.search(
                query=message,
                filters=entities,
                context=context
            )
        
        # Step 5: Generate LLM response
        response = await self.generate_response(
            message=message,
            intent=intent,
            context=augmented_context,
            products=products
        )
        
        # Step 6: Validate response quality
        if not self.validate_response(response):
            response = await self.fallback_response(message, context)
        
        # Step 7: Check for escalation triggers
        should_escalate = await self.check_escalation(message, response, context)
        if should_escalate:
            await self.escalate_to_human(context, reason=should_escalate.reason)
        
        # Step 8: Log analytics
        await self.analytics.track_conversation(
            store_id=context.store_id,
            message=message,
            response=response,
            intent=intent,
            products_shown=len(products)
        )
        
        return response
```

### Intent Classification

**Purpose:** Determine what the customer is trying to do

**Method:** Keyword matching + semantic similarity (fast, accurate enough)

```python
class IntentClassifier:
    """
    Classifies customer intent using hybrid approach:
    1. Rule-based matching (fast, handles common cases)
    2. Semantic similarity (handles edge cases)
    """
    
    INTENT_KEYWORDS = {
        'product_search': [
            'show', 'find', 'looking for', 'need', 'want', 'do you have',
            'searching for', 'browse', 'recommendations'
        ],
        'order_tracking': [
            'order', 'track', 'shipping', 'delivery', 'where is',
            'when will', 'status', 'eta'
        ],
        'support': [
            'help', 'problem', 'issue', 'broken', 'doesn\'t work',
            'refund', 'return', 'exchange', 'complaint'
        ],
        'sizing': [
            'size', 'fit', 'measurements', 'run true', 'big', 'small',
            'length', 'width'
        ],
        'policy': [
            'shipping policy', 'return policy', 'warranty', 'guarantee',
            'how long', 'free shipping'
        ]
    }
    
    def classify(self, message: str, context: ConversationContext) -> str:
        message_lower = message.lower()
        
        # Rule-based matching (covers 80% of cases)
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        # Semantic similarity (covers edge cases)
        # Compare message embedding to intent examples
        message_embedding = self.embedding_model.encode(message)
        
        similarities = {}
        for intent, examples in self.INTENT_EXAMPLES.items():
            example_embeddings = self.embedding_model.encode(examples)
            similarity = cosine_similarity(message_embedding, example_embeddings)
            similarities[intent] = max(similarity)
        
        # Return most similar intent if confidence > 0.7
        best_intent = max(similarities, key=similarities.get)
        if similarities[best_intent] > 0.7:
            return best_intent
        
        return 'general'  # Default fallback
```

### Entity Extraction

**Purpose:** Extract structured information from unstructured text

**Examples:**
- "Show me red dresses under $50" → {category: 'dresses', color: 'red', max_price: 50}
- "Size 10 waterproof boots" → {size: '10', attributes: ['waterproof'], category: 'boots'}

```python
class EntityExtractor:
    """
    Extracts structured entities from customer messages.
    
    Uses regex + NLP for high accuracy.
    """
    
    PATTERNS = {
        'price': r'\$?(\d+(?:\.\d{2})?)',  # Matches: $50, 50, 49.99
        'size': r'\b(size|sz)?\s*([0-9]{1,2}(?:\.[0-9])?|(?:xx?)?[smlx]{1,3})\b',
        'color': r'\b(red|blue|green|black|white|pink|yellow|orange|purple|gray|brown)\b',
        'material': r'\b(leather|cotton|wool|silk|polyester|denim|suede)\b'
    }
    
    def extract(self, message: str) -> Dict[str, Any]:
        entities = {}
        message_lower = message.lower()
        
        # Extract price range
        prices = re.findall(self.PATTERNS['price'], message_lower)
        if prices:
            entities['max_price'] = max(float(p) for p in prices)
        
        # Extract sizes
        size_matches = re.findall(self.PATTERNS['size'], message_lower)
        if size_matches:
            entities['size'] = [match[1] for match in size_matches]
        
        # Extract colors
        colors = re.findall(self.PATTERNS['color'], message_lower)
        if colors:
            entities['colors'] = colors
        
        # Extract materials
        materials = re.findall(self.PATTERNS['material'], message_lower)
        if materials:
            entities['materials'] = materials
        
        # Extract product categories using NER (Named Entity Recognition)
        # Simple implementation: match against known product types
        for category in self.PRODUCT_CATEGORIES:
            if category.lower() in message_lower:
                entities['category'] = category
                break
        
        return entities
```

### Response Generation

**Purpose:** Craft natural, helpful responses using Llama 3

```python
class ResponseGenerator:
    """
    Generates AI responses using Llama 3.1 via Groq API.
    
    Key responsibilities:
    - Prompt engineering
    - API call management
    - Response parsing
    """
    
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = "llama-3.1-70b-versatile"
    
    async def generate(self, 
                      message: str,
                      context: ConversationContext,
                      products: List[Product] = None) -> str:
        """
        Generate response using Llama 3.
        
        Args:
            message: Customer's message
            context: Full conversation context
            products: Relevant products to mention (if any)
        
        Returns:
            Natural language response
        """
        
        # Build system prompt
        system_prompt = self.build_system_prompt(context)
        
        # Build user prompt with context
        user_prompt = self.build_user_prompt(message, context, products)
        
        # Call Groq API
        response = await self.groq_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                *self.format_conversation_history(context.history),
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Slightly creative but not too random
            max_tokens=300,   # Keep responses concise
            top_p=0.9,
            stream=False
        )
        
        return response.choices[0].message.content
    
    def build_system_prompt(self, context: ConversationContext) -> str:
        """
        Create dynamic system prompt based on store and context.
        """
        store = context.store
        
        prompt = f"""You are a helpful AI shopping assistant for {store.name}.

Store description: {store.description}

Your role:
1. Help customers find products they'll love
2. Answer questions about products, shipping, and policies
3. Be friendly, concise, and helpful

Guidelines:
- Keep responses under 3 sentences unless customer asks for details
- Always mention product names and prices when recommending
- If you don't know something, say "Let me check with the team"
- Use 1-2 emojis max per response
- Create gentle urgency if stock is low

Store policies:
- Shipping: {store.shipping_policy}
- Returns: {store.return_policy}
- Payment: {store.payment_methods}

Current context:
- Customer is viewing: {context.current_page}
- Cart items: {len(context.cart_items)} items, ${context.cart_total}
"""
        
        return prompt
    
    def build_user_prompt(self, 
                         message: str, 
                         context: ConversationContext,
                         products: List[Product]) -> str:
        """
        Build user prompt with all relevant info.
        """
        prompt = f"Customer message: {message}\n\n"
        
        if products:
            prompt += "Relevant products:\n"
            for i, product in enumerate(products[:5], 1):
                prompt += f"{i}. {product.title} - ${product.price}\n"
                prompt += f"   {product.short_description}\n"
                if product.inventory_quantity < 10:
                    prompt += f"   ⚡ Only {product.inventory_quantity} left\n"
            prompt += "\n"
        
        if context.cart_items:
            prompt += f"Customer has {len(context.cart_items)} items in cart.\n\n"
        
        prompt += "Respond naturally and helpfully:"
        
        return prompt
```

---

## Product Intelligence System

### Purpose
Understand the entire product catalog semantically to enable natural language search and recommendations.

### Architecture

```
Shopify Products (JSON)
        ↓
Product Processor
        ↓
┌───────────────────────────────┐
│ Text Preparation              │
│ "Title + Description +        │
│  Category + Key Attributes"   │
└────────────┬──────────────────┘
             ↓
Embedding Model (all-MiniLM-L6-v2)
             ↓
384-dimensional Vector
             ↓
Pinecone Vector DB
(Indexed for fast search)
```

### Implementation

```python
class ProductIntelligence:
    """
    Manages product catalog understanding and search.
    
    Core capabilities:
    - Semantic product search
    - Attribute filtering
    - Inventory-aware ranking
    """
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_db = pinecone.Index('sunsetbot-products')
    
    async def sync_catalog(self, store_id: str):
        """
        Sync entire product catalog from Shopify to vector DB.
        
        This runs:
        - On initial installation
        - Daily at 2 AM store timezone
        - When webhook triggered (product created/updated)
        """
        
        # Fetch all products from Shopify
        products = await shopify_api.get_all_products(store_id)
        
        # Process in batches (Pinecone limit: 100 vectors per upsert)
        batch_size = 100
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            # Generate embeddings
            vectors = await self.generate_product_embeddings(batch)
            
            # Upsert to Pinecone
            await self.vector_db.upsert(
                vectors=vectors,
                namespace=store_id  # Isolate each store's data
            )
        
        logger.info(f"Synced {len(products)} products for store {store_id}")
    
    def generate_product_embeddings(self, products: List[Product]) -> List[Vector]:
        """
        Convert products to vectors for semantic search.
        
        Strategy: Concatenate meaningful text fields and embed
        """
        vectors = []
        
        for product in products:
            # Build rich text representation
            text = self.build_product_text(product)
            
            # Generate embedding
            embedding = self.embedding_model.encode(text)
            
            # Prepare vector for Pinecone
            vectors.append({
                'id': product.shopify_id,
                'values': embedding.tolist(),
                'metadata': {
                    'title': product.title,
                    'price': float(product.price),
                    'category': product.category,
                    'tags': product.tags,
                    'inventory': product.inventory_quantity,
                    'image_url': product.images[0] if product.images else None,
                    'url': product.url
                }
            })
        
        return vectors
    
    def build_product_text(self, product: Product) -> str:
        """
        Create rich text representation for embedding.
        
        Includes:
        - Title (weighted 3x via repetition)
        - Description
        - Category
        - Key attributes (color, material, etc.)
        - Tags
        """
        parts = [
            product.title,
            product.title,  # Repeat title for higher weight
            product.title,
            product.description,
            product.category,
            ' '.join(product.tags),
        ]
        
        # Add variant attributes
        for variant in product.variants:
            if variant.color:
                parts.append(f"color {variant.color}")
            if variant.size:
                parts.append(f"size {variant.size}")
            if variant.material:
                parts.append(f"material {variant.material}")
        
        return ' '.join(filter(None, parts))
    
    async def search(self, 
                    query: str,
                    store_id: str,
                    filters: Dict = None,
                    top_k: int = 10) -> List[Product]:
        """
        Semantic product search.
        
        Args:
            query: Natural language query ("red dresses under $50")
            store_id: Which store's catalog to search
            filters: Extracted entities (price, color, etc.)
            top_k: Number of results to return
        
        Returns:
            Ranked list of matching products
        """
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)
        
        # Build Pinecone filter
        pinecone_filter = self.build_filter(filters) if filters else {}
        
        # Vector search
        results = await self.vector_db.query(
            vector=query_embedding.tolist(),
            top_k=top_k * 2,  # Get extra, then filter
            namespace=store_id,
            filter=pinecone_filter,
            include_metadata=True
        )
        
        # Convert to Product objects
        products = []
        for match in results.matches:
            product = Product(
                id=match.id,
                title=match.metadata['title'],
                price=match.metadata['price'],
                category=match.metadata['category'],
                image_url=match.metadata['image_url'],
                url=match.metadata['url'],
                inventory=match.metadata['inventory'],
                relevance_score=match.score
            )
            products.append(product)
        
        # Re-rank by multiple factors
        ranked_products = self.rerank(products, query, filters)
        
        return ranked_products[:top_k]
    
    def build_filter(self, filters: Dict) -> Dict:
        """
        Convert extracted entities to Pinecone filter format.
        """
        pinecone_filter = {}
        
        if 'max_price' in filters:
            pinecone_filter['price'] = {'$lte': filters['max_price']}
        
        if 'colors' in filters:
            # Pinecone metadata filtering
            pinecone_filter['tags'] = {'$in': filters['colors']}
        
        if 'category' in filters:
            pinecone_filter['category'] = filters['category']
        
        # Filter out out-of-stock items
        pinecone_filter['inventory'] = {'$gt': 0}
        
        return pinecone_filter
    
    def rerank(self, 
              products: List[Product], 
              query: str,
              filters: Dict = None) -> List[Product]:
        """
        Re-rank products using multiple signals.
        
        Ranking factors:
        1. Vector similarity (60% weight) - semantic relevance
        2. Inventory level (20% weight) - prefer in-stock items
        3. Sales velocity (10% weight) - prefer popular items
        4. Price match (10% weight) - prefer items in budget
        """
        
        for product in products:
            score = 0
            
            # Vector similarity (already computed)
            score += product.relevance_score * 0.6
            
            # Inventory score
            if product.inventory > 10:
                score += 0.2
            elif product.inventory > 0:
                score += 0.1 * (product.inventory / 10)
            
            # Sales velocity (would need historical data)
            # For now, use a placeholder
            score += 0.1
            
            # Price match
            if filters and 'max_price' in filters:
                if product.price <= filters['max_price']:
                    score += 0.1
            else:
                score += 0.1  # No penalty if no price filter
            
            product.final_score = score
        
        # Sort by final score
        products.sort(key=lambda p: p.final_score, reverse=True)
        
        return products
```

---

## Recommendation Engine

### Types of Recommendations

1. **Similar Items** - Vector similarity
2. **Frequently Bought Together** - Collaborative filtering
3. **Upsells** - Same category, higher price
4. **Cross-sells** - Complementary products

### Implementation

```python
class RecommendationEngine:
    """
    Generates personalized product recommendations.
    """
    
    async def get_similar_products(self, 
                                   product_id: str,
                                   store_id: str,
                                   top_k: int = 5) -> List[Product]:
        """
        Find products similar to a given product.
        
        Method: Vector similarity search
        """
        
        # Get embedding of target product
        product_embedding = await self.vector_db.fetch(
            ids=[product_id],
            namespace=store_id
        )
        
        # Search for similar vectors
        similar = await self.vector_db.query(
            vector=product_embedding.vectors[product_id],
            top_k=top_k + 1,  # +1 because it includes itself
            namespace=store_id
        )
        
        # Remove the product itself from results
        similar_products = [p for p in similar.matches if p.id != product_id]
        
        return similar_products[:top_k]
    
    async def get_frequently_bought_together(self,
                                            product_id: str,
                                            store_id: str,
                                            top_k: int = 3) -> List[Product]:
        """
        Find products frequently bought with this product.
        
        Method: Analyze historical order data
        """
        
        # Query order history
        query = """
        SELECT 
            oi2.product_id,
            COUNT(*) as frequency,
            AVG(o.total_price) as avg_order_value
        FROM orders o
        JOIN order_items oi1 ON o.id = oi1.order_id
        JOIN order_items oi2 ON o.id = oi2.order_id
        WHERE oi1.product_id = %s
          AND oi2.product_id != %s
          AND o.store_id = %s
          AND o.created_at > NOW() - INTERVAL '90 days'
        GROUP BY oi2.product_id
        ORDER BY frequency DESC, avg_order_value DESC
        LIMIT %s
        """
        
        results = await db.query(query, [product_id, product_id, store_id, top_k])
        
        # Fetch full product details
        product_ids = [r['product_id'] for r in results]
        products = await self.get_products_by_ids(product_ids, store_id)
        
        return products
    
    async def get_upsell_recommendations(self,
                                        product: Product,
                                        store_id: str,
                                        top_k: int = 3) -> List[Product]:
        """
        Find upsell opportunities (better/more expensive alternatives).
        
        Criteria:
        - Same category
        - 20-100% higher price
        - Higher quality indicators (reviews, features)
        """
        
        filter_conditions = {
            'category': product.category,
            'price': {
                '$gte': product.price * 1.2,
                '$lte': product.price * 2.0
            },
            'inventory': {'$gt': 0}
        }
        
        # Search with category constraint
        query_embedding = await self.get_product_embedding(product.id, store_id)
        
        results = await self.vector_db.query(
            vector=query_embedding,
            top_k=top_k * 2,
            namespace=store_id,
            filter=filter_conditions
        )
        
        # Prioritize by features/reviews
        ranked = sorted(results.matches, 
                       key=lambda p: (
                           p.metadata.get('review_score', 0),
                           p.metadata.get('feature_count', 0)
                       ),
                       reverse=True)
        
        return ranked[:top_k]
```

---

## Context Management

### Session Context

```python
@dataclass
class ConversationContext:
    """
    Stores all contextual information about a conversation.
    
    This is passed to every AI function to ensure consistent,
    contextually-aware responses.
    """
    
    # Identifiers
    session_id: str
    store_id: str
    customer_id: Optional[str] = None
    
    # Store info
    store: Store = None
    
    # Conversation state
    history: List[Message] = field(default_factory=list)
    intent: str = 'browsing'  # browsing | purchasing | support
    sentiment: str = 'neutral'  # positive | neutral | negative
    
    # Customer behavior
    viewed_products: List[str] = field(default_factory=list)
    cart_items: List[CartItem] = field(default_factory=list)
    cart_total: Decimal = Decimal('0.00')
    
    # Page context
    current_page: str = 'home'
    referrer: Optional[str] = None
    
    # Customer data (if logged in)
    customer_email: Optional[str] = None
    previous_orders: List[Order] = field(default_factory=list)
    lifetime_value: Decimal = Decimal('0.00')
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str):
        """Add message to history and update activity timestamp."""
        self.history.append(Message(role=role, content=content))
        self.last_activity = datetime.now()
    
    def get_recent_history(self, n: int = 10) -> List[Message]:
        """Get last N messages for LLM context."""
        return self.history[-n:]
    
    def is_vip(self) -> bool:
        """Check if customer is VIP (high lifetime value)."""
        return self.lifetime_value > 1000
```

### Context Storage

**Short-term:** Redis (session cache)
- Expires after 1 hour of inactivity
- Fast access (<1ms)
- Used for active conversations

**Long-term:** PostgreSQL
- Permanent storage
- Used for analytics
- Enables personalization across sessions

```python
class ContextManager:
    """
    Manages conversation context across sessions.
    """
    
    async def get_context(self, session_id: str) -> ConversationContext:
        """
        Load conversation context from cache or DB.
        """
        
        # Try cache first
        cached = await redis.get(f'context:{session_id}')
        if cached:
            return ConversationContext.from_json(cached)
        
        # Fall back to database
        db_context = await db.conversations.find_one({'session_id': session_id})
        if db_context:
            context = ConversationContext.from_db(db_context)
            await self.cache_context(context)
            return context
        
        # Create new context
        return ConversationContext(session_id=session_id)
    
    async def save_context(self, context: ConversationContext):
        """
        Save context to both cache and DB.
        """
        
        # Update cache (fast access)
        await redis.setex(
            f'context:{context.session_id}',
            3600,  # 1 hour TTL
            context.to_json()
        )
        
        # Update database (persistence)
        await db.conversations.update_one(
            {'session_id': context.session_id},
            {'$set': context.to_db()},
            upsert=True
        )
```

---

## Escalation Logic

### When to Escalate

```python
class EscalationHandler:
    """
    Determines when to hand off to human support.
    """
    
    async def check_escalation(self,
                               message: str,
                               response: str,
                               context: ConversationContext) -> Optional[EscalationTrigger]:
        """
        Analyze if conversation should escalate to human.
        
        Returns None if no escalation needed, otherwise returns
        EscalationTrigger with reason and priority.
        """
        
        triggers = []
        
        # 1. Sentiment Analysis
        sentiment_score = await self.analyze_sentiment(message)
        if sentiment_score < -0.6:  # Very negative
            triggers.append(EscalationTrigger(
                reason='negative_sentiment',
                priority='high',
                details=f'Sentiment score: {sentiment_score}'
            ))
        
        # 2. Confidence Check
        response_confidence = await self.estimate_confidence(response)
        if response_confidence < 0.6:
            triggers.append(EscalationTrigger(
                reason='low_confidence',
                priority='medium',
                details=f'Confidence: {response_confidence}'
            ))
        
        # 3. Keyword Triggers
        escalation_keywords = [
            'refund', 'manager', 'complaint', 'terrible',
            'worst', 'never again', 'lawyer', 'sue'
        ]
        if any(word in message.lower() for word in escalation_keywords):
            triggers.append(EscalationTrigger(
                reason='keyword_trigger',
                priority='high',
                details=f'Keyword match in: {message}'
            ))
        
        # 4. Repeated Questions
        if self.is_question_repeated(message, context.history):
            triggers.append(EscalationTrigger(
                reason='repeated_question',
                priority='medium',
                details='Customer asked same question 3+ times'
            ))
        
        # 5. VIP Customer
        if context.is_vip():
            triggers.append(EscalationTrigger(
                reason='vip_customer',
                priority='medium',
                details=f'LTV: ${context.lifetime_value}'
            ))
        
        # 6. High-value Refund Request
        if 'refund' in message.lower() and context.cart_total > 100:
            triggers.append(EscalationTrigger(
                reason='high_value_refund',
                priority='high',
                details=f'Cart value: ${context.cart_total}'
            ))
        
        # Return highest priority trigger
        if triggers:
            triggers.sort(key=lambda t: self.priority_score(t.priority), reverse=True)
            return triggers[0]
        
        return None
    
    async def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment using RoBERTa model.
        
        Returns: Score from -1 (very negative) to +1 (very positive)
        """
        
        result = self.sentiment_pipeline(text)[0]
        
        # Convert to numeric score
        if result['label'] == 'positive':
            return result['score']
        elif result['label'] == 'negative':
            return -result['score']
        else:
            return 0.0
    
    async def escalate(self,
                      context: ConversationContext,
                      trigger: EscalationTrigger):
        """
        Escalate conversation to human support.
        
        Actions:
        1. Notify store owner (email + SMS if high priority)
        2. Mark conversation as escalated
        3. Provide handoff message to customer
        4. Send full context to support dashboard
        """
        
        # 1. Send notifications
        await self.notify_owner(
            store_id=context.store_id,
            priority=trigger.priority,
            reason=trigger.reason,
            conversation_url=f'/admin/conversations/{context.session_id}'
        )
        
        # 2. Mark as escalated
        context.escalated = True
        context.escalation_reason = trigger.reason
        await context_manager.save_context(context)
        
        # 3. Send handoff message
        handoff_message = self.get_handoff_message(trigger.priority)
        await send_message(context.session_id, handoff_message)
        
        # 4. Log analytics
        await analytics.track_event(
            store_id=context.store_id,
            event_type='conversation_escalated',
            metadata={
                'reason': trigger.reason,
                'priority': trigger.priority,
                'conversation_id': context.session_id
            }
        )
```

---

## Performance & Scaling

### Latency Targets

| Component | Target | Current | Optimization |
|-----------|--------|---------|--------------|
| **Total Response Time** | <2s | 1.2s | ✅ |
| Vector Search | <50ms | 30ms | ✅ |
| LLM Generation | <1.5s | 800ms | ✅ (Groq is fast!) |
| DB Queries | <20ms | 15ms | ✅ |
| Embedding Generation | <100ms | 80ms | ✅ |

### Caching Strategy

```python
class CacheStrategy:
    """
    Multi-level caching for performance optimization.
    """
    
    # Level 1: In-memory (Python dict)
    # - Fastest (<1ms)
    # - Limited to single server
    # - Used for: Frequently accessed products
    
    # Level 2: Redis
    # - Fast (1-5ms)
    # - Shared across servers
    # - Used for: Sessions, product embeddings
    
    # Level 3: PostgreSQL
    # - Slower (10-50ms)
    # - Persistent storage
    # - Used for: Analytics, conversation history
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """
        Try cache levels in order.
        """
        
        # Level 1: Memory
        if product_id in self.memory_cache:
            return self.memory_cache[product_id]
        
        # Level 2: Redis
        cached = await redis.get(f'product:{product_id}')
        if cached:
            product = Product.from_json(cached)
            self.memory_cache[product_id] = product  # Warm memory cache
            return product
        
        # Level 3: Database
        product = await db.products.find_one({'id': product_id})
        if product:
            # Warm both caches
            await redis.setex(f'product:{product_id}', 300, product.to_json())
            self.memory_cache[product_id] = product
            return product
        
        return None
```

### Scaling Plan

**Phase 1: 1-50 customers (Current)**
- Single backend server (Railway)
- Free tier databases
- Cost: $20/month

**Phase 2: 50-200 customers**
- 2-3 backend servers (load balanced)
- Paid database tier
- CDN for static assets
- Cost: $150/month

**Phase 3: 200-1000 customers**
- Auto-scaling backend (5-10 servers)
- Database read replicas
- Dedicated Redis cluster
- Cost: $800/month

---

## Monitoring & Observability

### Key Metrics

```python
# Application Performance
- Response time (p50, p95, p99)
- Error rate (5xx errors)
- Request rate (requests/second)
- Active conversations (concurrent)

# AI Performance  
- LLM response time
- Vector search latency
- Embedding generation time
- Confidence scores (average)

# Business Metrics
- Conversation → Purchase rate
- Escalation rate
- Customer satisfaction (1-5 stars)
- Products recommended vs. added to cart

# Infrastructure
- CPU usage
- Memory usage
- Database connection pool
- Redis hit rate
```

### Logging

```python
import structlog

logger = structlog.get_logger()

# Structured logging for easy analysis
logger.info(
    "conversation_completed",
    session_id=session_id,
    store_id=store_id,
    message_count=len(context.history),
    resulted_in_purchase=bool(context.order_id),
    duration_seconds=(context.ended_at - context.started_at).total_seconds(),
    sentiment=context.sentiment,
    escalated=context.escalated
)
```

### Error Tracking

```python
# Sentry integration for error tracking
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    traces_sample_rate=0.1,  # Sample 10% of transactions
    environment='production'
)

# Errors automatically captured with context
try:
    response = await generate_response(message, context)
except Exception as e:
    sentry_sdk.capture_exception(e)
    # Fallback to safe response
    response = "I'm having trouble right now. Let me connect you with a team member."
```

---

## Future Enhancements

### Short-term (Months 3-6)

1. **Fine-tuning Llama 3**
   - Train on actual conversations
   - Improve product knowledge
   - Reduce hallucinations

2. **Advanced Recommendations**
   - Collaborative filtering (user-user similarity)
   - Real-time inventory optimization
   - Seasonal trends

3. **Multi-language Support**
   - Detect customer language
   - Translate products/responses
   - Support 10+ languages

### Long-term (Months 6-12)

1. **Voice Commerce**
   - Voice input/output
   - Phone integration
   - Voice-optimized prompts

2. **Predictive Analytics**
   - Predict which customers will buy
   - Predict which products to stock
   - Predict churn risk

3. **Visual Search**
   - "Find similar to this image"
   - Style matching
   - Color extraction

---

**END OF AI ARCHITECTURE DOCUMENT**

This architecture is designed to be scalable, maintainable, and performant from day 1 through 1000+ customers.
