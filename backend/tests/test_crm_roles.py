"""Managers run the order desk; only administrators change the catalogue."""
import pytest
from conftest import ADMIN, stock_of, variant_id

from app.models import Order, OrderStatus, Role, User
from app.security import password_hash

MANAGER = {"email": "manager@briefs.store", "password": "manager-secret"}
ORDER = {"email": "shopper@briefs.store", "name": "Shopper", "delivery_address": "Kyiv, Nova Poshta 1"}


@pytest.fixture
def manager(client, db_session):
    with db_session() as session:
        session.add(User(email=MANAGER["email"], password_hash=password_hash(MANAGER["password"]), role=Role.MANAGER))
        session.commit()
    client.post("/admin/login", data=MANAGER)
    return client


@pytest.fixture
def admin(client):
    client.post("/admin/login", data=ADMIN)
    return client


def place_order(client, db_session, quantity: int = 3) -> int:
    return client.post("/api/v1/orders", json={**ORDER, "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": quantity}]}).json()["id"]


def test_manager_can_move_an_order_along(manager, client, db_session):
    order_id = place_order(client, db_session, 1)
    response = manager.patch(f"/admin/orders/{order_id}/status", data={"status": "shipped"})
    assert response.status_code == 200

    with db_session() as session:
        assert session.get(Order, order_id).status == OrderStatus.SHIPPED


def test_manager_cannot_change_prices(manager, db_session):
    target = variant_id(db_session, "EDC-BLK-M")
    response = manager.patch(f"/admin/variants/{target}", data={"price": "1", "stock": "99"})
    assert response.status_code == 403
    assert stock_of(db_session, "EDC-BLK-M") == 5


def test_manager_cannot_publish_or_hide_products(manager, client):
    product_id = client.get("/api/v1/products/soft-modal").json()["id"]
    assert manager.post(f"/admin/products/{product_id}/visibility").status_code == 403
    assert client.get("/api/v1/products/soft-modal").status_code == 200


def test_administrator_still_can(admin, db_session):
    target = variant_id(db_session, "EDC-BLK-M")
    assert admin.patch(f"/admin/variants/{target}", data={"price": "600", "stock": "7"}).status_code == 200
    assert stock_of(db_session, "EDC-BLK-M") == 7


def test_cancelling_an_order_puts_the_stock_back(admin, client, db_session):
    order_id = place_order(client, db_session, 3)
    assert stock_of(db_session, "EDC-BLK-M") == 2

    assert admin.patch(f"/admin/orders/{order_id}/status", data={"status": "cancelled"}).status_code == 200
    assert stock_of(db_session, "EDC-BLK-M") == 5


def test_a_cancelled_order_cannot_be_reopened(admin, client, db_session):
    order_id = place_order(client, db_session, 3)
    admin.patch(f"/admin/orders/{order_id}/status", data={"status": "cancelled"})

    response = admin.patch(f"/admin/orders/{order_id}/status", data={"status": "paid"})
    assert response.status_code == 409
    assert stock_of(db_session, "EDC-BLK-M") == 5
    with db_session() as session:
        assert session.get(Order, order_id).status == OrderStatus.CANCELLED


def test_cancelling_twice_does_not_duplicate_stock(admin, client, db_session):
    order_id = place_order(client, db_session, 3)
    admin.patch(f"/admin/orders/{order_id}/status", data={"status": "cancelled"})
    admin.patch(f"/admin/orders/{order_id}/status", data={"status": "cancelled"})
    assert stock_of(db_session, "EDC-BLK-M") == 5
