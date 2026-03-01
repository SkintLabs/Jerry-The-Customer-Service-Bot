"""
Jerry The Customer Service Bot — Analytics Service
Tracks chat sessions, support resolutions, and attributed sales.
Replaces the _AnalyticsServiceStub in conversation_engine.py.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, and_

from app.db.engine import get_db
from app.db.models import Store, ChatSession, SupportResolution, AttributedSale

logger = logging.getLogger("jerry.analytics")


class AnalyticsService:
    """
    Real analytics service for tracking usage and billing events.
    Writes to PostgreSQL and optionally reports metered usage to Stripe.
    """

    def __init__(self, billing_service=None):
        self.billing_service = billing_service
        logger.info(
            f"AnalyticsService initialized "
            f"(billing={'connected' if billing_service and billing_service.configured else 'disabled'})"
        )

    async def track_conversation(
        self,
        store_id: str,
        session_id: str,
        message: str,
        response_text: str,
        intent: str,
        entities: dict,
        products_shown: int,
        escalated: bool,
    ) -> None:
        """
        Called by ConversationEngine after every message.
        Creates a ChatSession on first message, increments store usage.
        """
        try:
            async with get_db() as db:
                # Find store by store_id (domain prefix)
                store_domain = f"{store_id}.myshopify.com"
                result = await db.execute(
                    select(Store).where(Store.shopify_domain == store_domain)
                )
                store = result.scalar_one_or_none()

                if not store:
                    # Try matching store_id directly (dev mode)
                    result = await db.execute(
                        select(Store).where(Store.shopify_domain.contains(store_id))
                    )
                    store = result.scalar_one_or_none()

                if not store:
                    logger.debug(f"Store not found for {store_id} — skipping analytics")
                    return

                # Check if session already exists
                session_result = await db.execute(
                    select(ChatSession).where(ChatSession.session_token == session_id)
                )
                session = session_result.scalar_one_or_none()

                if not session:
                    # New session — create and increment usage
                    session = ChatSession(
                        merchant_id=store.id,
                        session_token=session_id,
                        human_intervention=escalated,
                    )
                    db.add(session)
                    store.current_month_usage += 1
                    logger.info(
                        f"New session tracked | store={store_id} | session={session_id} | "
                        f"usage={store.current_month_usage}/{store.monthly_interaction_limit}"
                    )
                elif escalated and not session.human_intervention:
                    session.human_intervention = True

        except Exception as e:
            logger.error(f"Analytics tracking failed: {e}", exc_info=True)

    async def record_resolution(
        self,
        store_id: str,
        session_id: str,
        resolution_type: str,
    ) -> None:
        """
        Called when a support interaction is resolved.
        Records the resolution and reports to Stripe billing.
        """
        try:
            async with get_db() as db:
                store_domain = f"{store_id}.myshopify.com"
                result = await db.execute(
                    select(Store).where(Store.shopify_domain == store_domain)
                )
                store = result.scalar_one_or_none()
                if not store:
                    return

                # Find session
                session_result = await db.execute(
                    select(ChatSession).where(ChatSession.session_token == session_id)
                )
                session = session_result.scalar_one_or_none()

                resolution = SupportResolution(
                    merchant_id=store.id,
                    session_id=session.id if session else None,
                    resolution_type=resolution_type,
                )
                db.add(resolution)

                if session:
                    session.resolved = True

            # Report to Stripe (fire and forget)
            if self.billing_service and store.stripe_subscription_id:
                asyncio.create_task(
                    self.billing_service.report_resolution(
                        store.stripe_subscription_id,
                        store.jerry_plan,
                    )
                )

            logger.info(f"Resolution recorded | store={store_id} | type={resolution_type}")

        except Exception as e:
            logger.error(f"Resolution recording failed: {e}", exc_info=True)

    async def record_attributed_sale(
        self,
        shop_domain: str,
        shopify_order_id: str,
        order_value: float,
    ) -> None:
        """
        Called when an order is attributed to Jerry (via webhook).
        Records the sale and reports revenue share to Stripe.
        """
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(Store).where(Store.shopify_domain == shop_domain)
                )
                store = result.scalar_one_or_none()
                if not store:
                    return

                # Check if already recorded (idempotent)
                existing = await db.execute(
                    select(AttributedSale).where(
                        AttributedSale.shopify_order_id == shopify_order_id
                    )
                )
                if existing.scalar_one_or_none():
                    return

                from decimal import Decimal
                plan_config_map = {
                    "base": Decimal("0.02"),
                    "elite": Decimal("0.05"),
                }
                pct = plan_config_map.get(store.jerry_plan, Decimal("0.02"))
                order_value_cents = int(order_value * 100)
                commission = int(order_value_cents * pct)

                sale = AttributedSale(
                    merchant_id=store.id,
                    shopify_order_id=shopify_order_id,
                    order_value=order_value,
                    commission_cents=commission,
                )
                db.add(sale)

            # Report to Stripe
            if self.billing_service and store.stripe_subscription_id:
                asyncio.create_task(
                    self.billing_service.report_revenue_share(
                        store.stripe_subscription_id,
                        store.jerry_plan,
                        order_value_cents,
                    )
                )

            logger.info(
                f"Sale attributed | shop={shop_domain} | order={shopify_order_id} | "
                f"value={order_value} | commission={commission}c"
            )

        except Exception as e:
            logger.error(f"Sale attribution failed: {e}", exc_info=True)
