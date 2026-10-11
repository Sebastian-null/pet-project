from conftest import CUSTOMER, variant_id

FORM = {"email": "typed-by-hand@briefs.store", "name": "Shopper", "delivery_address": "Kyiv, Nova Poshta 1"}


def place(client, db_session, token: str | None = None, sku: str = "EDC-BLK-M"):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/v1/orders", headers=headers, json={**FORM, "items": [{"variant_id": variant_id(db_session, sku), "quantity": 1}]})


def test_orders_list_requires_a_token(client):
    assert client.get("/api/v1/account/orders").status_code == 401


def test_new_customer_starts_with_an_empty_list(client, customer_token):
    response = client.get("/api/v1/account/orders", headers={"Authorization": f"Bearer {customer_token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_order_placed_while_signed_in_belongs_to_the_account(client, db_session, customer_token):
    order_id = place(client, db_session, customer_token).json()["id"]

    orders = client.get("/api/v1/account/orders", headers={"Authorization": f"Bearer {customer_token}"}).json()
    assert [order["id"] for order in orders] == [order_id]
    assert orders[0]["items"][0]["quantity"] == 1

    # The signed-in account is used even though the form carried a different email.
    from app.models import Customer
    with db_session() as session:
        assert session.query(Customer).filter(Customer.email == FORM["email"]).count() == 0


def test_guest_order_does_not_show_up_in_another_account(client, db_session, customer_token):
    place(client, db_session)
    assert client.get("/api/v1/account/orders", headers={"Authorization": f"Bearer {customer_token}"}).json() == []


def test_orders_are_listed_newest_first(client, db_session, customer_token):
    first = place(client, db_session, customer_token).json()["id"]
    second = place(client, db_session, customer_token, sku="SMD-BLU-M").json()["id"]

    orders = client.get("/api/v1/account/orders", headers={"Authorization": f"Bearer {customer_token}"}).json()
    assert [order["id"] for order in orders] == [second, first]


def test_checkout_refreshes_the_profile_details(client, db_session, customer_token):
    place(client, db_session, customer_token)
    profile = client.get("/api/v1/account", headers={"Authorization": f"Bearer {customer_token}"}).json()
    assert profile["name"] == FORM["name"]
    assert profile["email"] == CUSTOMER["email"]
