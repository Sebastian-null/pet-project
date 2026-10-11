import logging
import time
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import inventory
from .config import settings
from .db import get_db
from .models import Order, OrderStatus
from .schemas import PaymentStatusOut

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])
SESSION_TTL_SECONDS = 30 * 60

def enabled() -> bool:
    return bool(settings.stripe_secret_key)

def client() -> stripe.StripeClient:
    if not settings.stripe_secret_key: raise HTTPException(status_code=503, detail="Payments are not configured")
    return stripe.StripeClient(settings.stripe_secret_key)

def minor_units(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def create_checkout_session(order: Order, locale: str) -> str:
    session = client().v1.checkout.sessions.create(params={
        "mode": "payment",
        "client_reference_id": str(order.id),
        "customer_email": order.customer.email,
        "expires_at": int(time.time()) + SESSION_TTL_SECONDS,
        "metadata": {"order_id": str(order.id)},
        "line_items": [{"quantity": item.quantity, "price_data": {"currency": settings.stripe_currency.lower(), "unit_amount": minor_units(item.unit_price), "product_data": {"name": item.title}}} for item in order.items],
        "success_url": f"{settings.storefront_url}/{locale}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.storefront_url}/{locale}/checkout/cancel?session_id={{CHECKOUT_SESSION_ID}}",
    })
    order.payment_session_id = session.id
    return session.url

def mark_paid(db: Session, order: Order, payment_intent_id: str | None) -> None:
    if order.status == OrderStatus.CANCELLED:
        log.warning("Order %s was paid after it had been cancelled; refund %s manually", order.id, payment_intent_id)
    if order.status != OrderStatus.NEW: return
    order.status, order.paid_at, order.payment_intent_id = OrderStatus.PAID, datetime.now(UTC), payment_intent_id
    db.commit()

def release(db: Session, order: Order) -> None:
    """Cancel an order that was never paid for and return its reserved units to stock."""
    if order.status != OrderStatus.NEW: return
    inventory.cancel(db, order)

@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, stripe_signature: str = Header(default=""), db: Session = Depends(get_db)):
    if not settings.stripe_webhook_secret: raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")
    try:
        event = stripe.Webhook.construct_event(await request.body(), stripe_signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from None
    if event["type"] not in {"checkout.session.completed", "checkout.session.async_payment_succeeded", "checkout.session.async_payment_failed", "checkout.session.expired"}:
        return {"received": True}
    session = event["data"]["object"]
    order = db.scalar(select(Order).where(Order.payment_session_id == session["id"]).options(selectinload(Order.items)))
    if not order: return {"received": True}
    if session["payment_status"] == "paid": mark_paid(db, order, session["payment_intent"])
    elif event["type"] in {"checkout.session.expired", "checkout.session.async_payment_failed"}: release(db, order)
    return {"received": True}

@router.get("/stripe/session/{session_id}", response_model=PaymentStatusOut)
def session_status(session_id: str, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.payment_session_id == session_id))
    if not order: raise HTTPException(status_code=404, detail="Payment session not found")
    # The webhook may still be in flight when Stripe redirects the customer back.
    if order.status == OrderStatus.NEW and enabled():
        session = client().v1.checkout.sessions.retrieve(session_id)
        if session.payment_status == "paid": mark_paid(db, order, session.payment_intent)
    return PaymentStatusOut(order_id=order.id, status=order.status, total=float(order.total))
