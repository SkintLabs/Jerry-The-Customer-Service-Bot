"""
================================================================================
Jerry The Customer Service Bot — Database Models
================================================================================
File:     app/db/models.py
Version:  1.0.0
Session:  5 (February 2026)

PURPOSE
-------
SQLAlchemy ORM models for Jerry The Customer Service Bot's persistent data layer.
Currently stores Shopify store info and OAuth tokens.
Uses async SQLAlchemy with SQLite (dev) or PostgreSQL (production).
================================================================================
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Float,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# Base class for all models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# ---------------------------------------------------------------------------
# Store model — one row per installed Shopify store
# ---------------------------------------------------------------------------

class Store(Base):
    """
    Represents a Shopify store that has installed Jerry The Customer Service Bot.

    Created during OAuth callback, updated on product sync and billing events.
    The access_token is the Shopify Admin API token — treat it like a password.
    """

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Shopify identity ---
    shopify_domain: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
        comment="e.g. my-cool-store.myshopify.com",
    )
    shopify_store_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="Shopify's numeric store ID (from Shop API response)",
    )
    access_token: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Shopify Admin API access token — NEVER expose in logs or API responses",
    )
    scopes: Mapped[str] = mapped_column(
        Text, nullable=False, default="read_products,read_orders",
        comment="Comma-separated OAuth scopes granted by the store owner",
    )

    # --- Store info (fetched from Shopify Shop API after install) ---
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shop_owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plan_name: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="Shopify plan (basic, shopify, advanced, plus)",
    )

    # --- Jerry The Customer Service Bot config ---
    sunsetbot_plan: Mapped[str] = mapped_column(
        String(32), default="trial",
        comment="Jerry The Customer Service Bot billing plan: trial | starter | pro",
    )
    widget_color: Mapped[str] = mapped_column(
        String(7), default="#FF6B35",
        comment="Primary widget color hex code",
    )
    welcome_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Custom welcome message (overrides default)",
    )

    # --- Sync state ---
    products_count: Mapped[int] = mapped_column(Integer, default=0)
    products_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="Last successful full product sync timestamp",
    )
    webhook_registered: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Status ---
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True,
        comment="False = uninstalled or suspended",
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False,
    )
    uninstalled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
    )

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Store id={self.id} domain={self.shopify_domain} active={self.is_active}>"

    @property
    def store_id_for_pinecone(self) -> str:
        """Namespace used in Pinecone for this store's products."""
        return self.shopify_domain.replace(".myshopify.com", "")
