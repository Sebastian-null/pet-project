from datetime import UTC, datetime, timedelta

from conftest import stock_of, variant_id

from app.maintenance import ABANDONED_AFTER, sweep
from app.models import EmailVerification, Order, OrderStatus

BUYER = {"email": "shopper@briefs.store", "name": "Shopper", "delivery_address": "Kyiv, Nova Poshta 1"}


def place_order(client, db_session, age: timedelta | None = None) -> int:
    order_id = client.post("/api/v1/orders", json={**BUYER, "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 2}]}).json()["id"]
    if age:
        with db_session() as session:
            session.get(Order, order_id).created_at = datetime.now(UTC) - age
            session.commit()
    return order_id


def run_sweep(db_session) -> tuple[int, int]:
    with db_session() as session:
        return sweep(session)


def test_abandoned_order_is_cancelled_and_stock_comes_back(client, db_session):
    order_id = place_order(client, db_session, age=ABANDONED_AFTER + timedelta(minutes=5))
    assert stock_of(db_session, "EDC-BLK-M") == 3

    cancelled, _ = run_sweep(db_session)
    assert cancelled == 1
    assert stock_of(db_session, "EDC-BLK-M") == 5
    with db_session() as session:
        assert session.get(Order, order_id).status == OrderStatus.CANCELLED


def test_fresh_order_is_left_alone(client, db_session):
    place_order(client, db_session)
    cancelled, _ = run_sweep(db_session)
    assert cancelled == 0
    assert stock_of(db_session, "EDC-BLK-M") == 3


def test_paid_order_is_never_touched(client, db_session):
    order_id = place_order(client, db_session, age=ABANDONED_AFTER + timedelta(hours=2))
    with db_session() as session:
        session.get(Order, order_id).status = OrderStatus.PAID
        session.commit()

    cancelled, _ = run_sweep(db_session)
    assert cancelled == 0
    assert stock_of(db_session, "EDC-BLK-M") == 3


def test_expired_verification_codes_are_removed(client, db_session, sent_codes):
    client.post("/api/v1/auth/register/request-code", json={"email": "buyer@briefs.store", "name": "Buyer", "password": "Sup3rSecret!"})
    with db_session() as session:
        session.query(EmailVerification).update({EmailVerification.expires_at: datetime.now(UTC) - timedelta(minutes=1)})
        session.commit()

    _, removed = run_sweep(db_session)
    assert removed == 1
    with db_session() as session:
        assert session.query(EmailVerification).count() == 0


def test_valid_verification_code_survives(client, db_session, sent_codes):
    client.post("/api/v1/auth/register/request-code", json={"email": "buyer@briefs.store", "name": "Buyer", "password": "Sup3rSecret!"})
    _, removed = run_sweep(db_session)
    assert removed == 0
