"""
Jerry The Customer Service Bot — Store Dashboard API
Provides merchant-facing stats and chat history.
"""

import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.db.engine import get_db
from app.db.models import Store, ChatSession, SupportResolution, AttributedSale

logger = logging.getLogger("jerry.dashboard")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/{store_domain}/stats")
async def get_dashboard_stats(store_domain: str):
    """Get store dashboard stats for the current billing period."""
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.shopify_domain == store_domain)
        )
        store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Count conversations, resolutions, and attributed revenue
    async with get_db() as db:
        conversations = (await db.execute(
            select(func.count(ChatSession.id)).where(ChatSession.merchant_id == store.id)
        )).scalar() or 0

        resolutions = (await db.execute(
            select(func.count(SupportResolution.id)).where(SupportResolution.merchant_id == store.id)
        )).scalar() or 0

        revenue_result = await db.execute(
            select(func.sum(AttributedSale.order_value)).where(AttributedSale.merchant_id == store.id)
        )
        attributed_revenue = revenue_result.scalar() or 0.0

    return {
        "store": store.shopify_domain,
        "name": store.name,
        "plan": store.jerry_plan,
        "subscription_status": getattr(store, "subscription_status", "none"),
        "usage": {
            "current": store.current_month_usage,
            "limit": store.monthly_interaction_limit,
            "billing_cycle_reset": store.billing_cycle_reset.isoformat() if store.billing_cycle_reset else None,
        },
        "totals": {
            "conversations": conversations,
            "resolutions": resolutions,
            "attributed_revenue": round(float(attributed_revenue), 2),
        },
    }


@router.get("/{store_domain}/attributed-sales")
async def get_attributed_sales(store_domain: str, limit: int = Query(default=50, le=200)):
    """Get list of individual attributed sales for a store."""
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.shopify_domain == store_domain)
        )
        store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    async with get_db() as db:
        result = await db.execute(
            select(AttributedSale)
            .where(AttributedSale.merchant_id == store.id)
            .order_by(AttributedSale.created_at.desc())
            .limit(limit)
        )
        sales = result.scalars().all()

    return {
        "store": store.shopify_domain,
        "currency": getattr(store, "currency", "AUD"),
        "sales": [
            {
                "id": s.id,
                "shopify_order_id": s.shopify_order_id,
                "order_value": round(float(s.order_value), 2),
                "commission_cents": s.commission_cents,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sales
        ],
    }


@router.get("/{store_domain}/revenue-chart")
async def get_revenue_chart(store_domain: str, days: int = Query(default=30, le=365)):
    """Get daily attributed revenue totals for charting (last N days)."""
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.shopify_domain == store_domain)
        )
        store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with get_db() as db:
        result = await db.execute(
            select(AttributedSale)
            .where(
                AttributedSale.merchant_id == store.id,
                AttributedSale.created_at >= cutoff,
            )
            .order_by(AttributedSale.created_at.asc())
        )
        sales = result.scalars().all()

    # Group by UTC date
    daily: dict = defaultdict(float)
    for s in sales:
        if s.created_at:
            date_key = s.created_at.strftime("%Y-%m-%d")
        else:
            continue
        daily[date_key] += float(s.order_value)

    # Build full date range (fill gaps with 0)
    chart_data = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        chart_data.append({"date": d, "revenue": round(daily.get(d, 0.0), 2)})

    return {
        "store": store.shopify_domain,
        "currency": getattr(store, "currency", "AUD"),
        "days": days,
        "chart": chart_data,
        "total": round(sum(daily.values()), 2),
    }


@router.get("/{store_domain}/recent-chats")
async def get_recent_chats(store_domain: str, limit: int = Query(default=20, le=100)):
    """Get recent chat sessions for a store."""
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.shopify_domain == store_domain)
        )
        store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    async with get_db() as db:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.merchant_id == store.id)
            .order_by(ChatSession.created_at.desc())
            .limit(limit)
        )
        sessions = result.scalars().all()

    return {
        "store": store.shopify_domain,
        "chats": [
            {
                "id": s.id,
                "session_token": s.session_token,
                "resolved": s.resolved,
                "human_intervention": s.human_intervention,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
    }
