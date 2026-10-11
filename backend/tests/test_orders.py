from conftest import stock_of, variant_id

BUYER = {"email": "shopper@briefs.store", "name": "Shopper", "phone": "+380671234567", "delivery_address": "Kyiv, Nova Poshta 1"}


def checkout(client, db_session, sku: str, quantity: int):
    return client.post("/api/v1/orders", json={**BUYER, "items": [{"variant_id": variant_id(db_session, sku), "quantity": quantity}]})


def test_checkout_creates_an_order_and_reserves_stock(client, db_session):
    response = checkout(client, db_session, "EDC-BLK-M", 2)
    assert response.status_code == 201

    order = response.json()
    assert order["status"] == "new"
    assert order["total"] == 1180.0
    assert order["items"][0]["quantity"] == 2
    assert stock_of(db_session, "EDC-BLK-M") == 3


def test_checkout_without_stripe_keys_returns_no_payment_link(client, db_session):
    order = checkout(client, db_session, "EDC-BLK-M", 1).json()
    assert order["payment_url"] is None


def test_checkout_refuses_to_oversell(client, db_session):
    response = checkout(client, db_session, "EDC-BLK-M", 6)
    assert response.status_code == 409
    assert stock_of(db_session, "EDC-BLK-M") == 5


def test_sold_out_variant_cannot_be_ordered(client, db_session):
    assert checkout(client, db_session, "EDC-BLK-L", 1).status_code == 409


def test_unknown_variant_is_rejected(client):
    response = client.post("/api/v1/orders", json={**BUYER, "items": [{"variant_id": 9999, "quantity": 1}]})
    assert response.status_code == 422


def test_empty_basket_is_rejected(client):
    assert client.post("/api/v1/orders", json={**BUYER, "items": []}).status_code == 422


def test_repeat_customer_is_matched_by_email(client, db_session):
    first = checkout(client, db_session, "EDC-BLK-M", 1).json()
    second = checkout(client, db_session, "SMD-BLU-M", 1).json()
    assert first["id"] != second["id"]

    from app.models import Customer
    with db_session() as session:
        assert session.query(Customer).filter(Customer.email == BUYER["email"]).count() == 1


def test_order_details_are_admin_only(client, db_session, admin_token):
    order_id = checkout(client, db_session, "EDC-BLK-M", 1).json()["id"]
    assert client.get(f"/api/v1/orders/{order_id}").status_code == 401

    response = client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["id"] == order_id
