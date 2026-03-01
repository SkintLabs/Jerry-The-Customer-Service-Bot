"""
Jerry The Customer Service Bot — Billing API Routes
Handles Stripe subscription management and webhook processing.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.db.engine import get_db
from app.db.models import Store
from sqlalchemy import select

logger = logging.getLogger("jerry.billing.api")

router = APIRouter(prefix="/billing", tags=["Billing"])


class CreateSubscriptionRequest(BaseModel):
    shop_domain: str
    plan: str = "base"  # "base" or "elite"


@router.post("/create-subscription")
async def create_subscription(req: CreateSubscriptionRequest):
    """Create a Stripe subscription for a merchant."""
    # Import billing service from app state
    from main import billing_service

    if not billing_service or not billing_service.configured:
        raise HTTPException(status_code=503, detail="Billing not configured")

    # Find store
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.shopify_domain == req.shop_domain)
        )
        store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Create Stripe customer if needed
    if not store.stripe_customer_id:
        customer_id = await billing_service.create_customer(store)
        if not customer_id:
            raise HTTPException(status_code=500, detail="Failed to create Stripe customer")
        async with get_db() as db:
            result = await db.execute(
                select(Store).where(Store.id == store.id)
            )
            store = result.scalar_one()
            store.stripe_customer_id = customer_id
    else:
        customer_id = store.stripe_customer_id

    # Create subscription
    sub_result = await billing_service.create_subscription(customer_id, req.plan)
    if not sub_result:
        raise HTTPException(status_code=500, detail="Failed to create subscription")

    # Save subscription ID to store
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.id == store.id)
        )
        store = result.scalar_one()
        store.stripe_subscription_id = sub_result["subscription_id"]
        store.jerry_plan = req.plan

    return {
        "status": "subscription_created",
        "subscription_id": sub_result["subscription_id"],
        "client_secret": sub_result.get("client_secret"),
        "plan": req.plan,
    }


@router.post("/webhooks")
async def stripe_webhooks(request: Request):
    """Process Stripe webhook events."""
    from main import billing_service

    if not billing_service or not billing_service.configured:
        return Response(status_code=200)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = await billing_service.handle_webhook_event(payload, sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook")

    event_type = event["type"]

    if event_type == "invoice.paid":
        logger.info(f"Invoice paid: {event['data']['object']['id']}")
    elif event_type == "customer.subscription.updated":
        sub = event["data"]["object"]
        logger.info(f"Subscription updated: {sub['id']} status={sub['status']}")
    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        logger.info(f"Subscription cancelled: {sub['id']}")
    else:
        logger.info(f"Unhandled Stripe event: {event_type}")

    return Response(status_code=200)


@router.get("/usage/{store_domain}")
async def get_usage(store_domain: str):
    """Get current billing cycle usage for a store."""
    async with get_db() as db:
        result = await db.execute(
            select(Store).where(Store.shopify_domain == store_domain)
        )
        store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return {
        "store": store.shopify_domain,
        "plan": store.jerry_plan,
        "usage": store.current_month_usage,
        "limit": store.monthly_interaction_limit,
        "billing_cycle_reset": store.billing_cycle_reset.isoformat() if store.billing_cycle_reset else None,
    }
