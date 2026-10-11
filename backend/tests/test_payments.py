import hashlib
import hmac
import json
import time
from decimal import Decimal

from conftest import stock_of, variant_id

from app import payments
from app.models import Order, OrderStatus

BUYER = {"email": "shopper@briefs.store", "name": "Shopper", "delivery_address": "Kyiv, Nova Poshta 1"}
SESSION_ID = "cs_test_session"


def place_order(client, db_session, quantity: int = 2) -> int:
    response = client.post("/api/v1/orders", json={**BUYER, "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": quantity}]})
    order_id = response.json()["id"]
    with db_session() as session:
        session.get(Order, order_id).payment_session_id = SESSION_ID
        session.commit()
    return order_id


def stripe_event(event_type: str, payment_status: str) -> tuple[bytes, dict[str, str]]:
    payload = json.dumps({
        "id": "evt_test",
        "type": event_type,
        "data": {"object": {"id": SESSION_ID, "payment_status": payment_status, "payment_intent": "pi_test"}},
    }).encode()
    timestamp = int(time.time())
    signature = hmac.new(b"whsec_test_secret", f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return payload, {"Stripe-Signature": f"t={timestamp},v1={signature}", "Content-Type": "application/json"}


def order_status(db_session, order_id: int) -> OrderStatus:
    with db_session() as session:
        return session.get(Order, order_id).status


def test_prices_are_converted_to_stripe_minor_units():
    assert payments.minor_units(Decimal("590.00")) == 59000
    assert payments.minor_units(Decimal("0.01")) == 1
    assert payments.minor_units(Decimal("12.345")) == 1235


def test_forged_webhook_is_refused(client):
    response = client.post(
        "/api/v1/payments/stripe/webhook",
        content=b'{"type": "checkout.session.completed"}',
        headers={"Stripe-Signature": "t=1,v1=forged", "Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_paid_webhook_marks_the_order_paid(client, db_session):
    order_id = place_order(client, db_session)
    payload, headers = stripe_event("checkout.session.completed", "paid")

    assert client.post("/api/v1/payments/stripe/webhook", content=payload, headers=headers).status_code == 200
    assert order_status(db_session, order_id) == OrderStatus.PAID
    assert stock_of(db_session, "EDC-BLK-M") == 3


def test_paid_webhook_is_safe_to_replay(client, db_session):
    order_id = place_order(client, db_session)
    payload, headers = stripe_event("checkout.session.completed", "paid")

    client.post("/api/v1/payments/stripe/webhook", content=payload, headers=headers)
    with db_session() as session:
        paid_at = session.get(Order, order_id).paid_at

    client.post("/api/v1/payments/stripe/webhook", content=payload, headers=headers)
    with db_session() as session:
        assert session.get(Order, order_id).paid_at == paid_at


def test_expired_session_cancels_the_order_and_returns_stock(client, db_session):
    order_id = place_order(client, db_session)
    payload, headers = stripe_event("checkout.session.expired", "unpaid")

    assert client.post("/api/v1/payments/stripe/webhook", content=payload, headers=headers).status_code == 200
    assert order_status(db_session, order_id) == OrderStatus.CANCELLED
    assert stock_of(db_session, "EDC-BLK-M") == 5


def test_unrelated_events_are_acknowledged_without_changes(client, db_session):
    order_id = place_order(client, db_session)
    payload, headers = stripe_event("checkout.session.async_payment_failed", "unpaid")
    client.post("/api/v1/payments/stripe/webhook", content=payload, headers=headers)
    assert order_status(db_session, order_id) == OrderStatus.CANCELLED


def test_checkout_returns_the_stripe_payment_link(client, db_session, monkeypatch):
    monkeypatch.setattr(payments, "enabled", lambda: True)
    monkeypatch.setattr(payments, "create_checkout_session", lambda order, locale: f"https://checkout.stripe.test/{order.id}/{locale}")

    response = client.post("/api/v1/orders", json={**BUYER, "locale": "en", "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 1}]})
    assert response.status_code == 201
    assert response.json()["payment_url"].endswith("/en")
