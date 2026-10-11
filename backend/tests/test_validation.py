import pytest
from conftest import ADMIN, CUSTOMER, variant_id

ORDER = {"email": "shopper@briefs.store", "name": "Shopper", "delivery_address": "Kyiv, Nova Poshta 1"}


@pytest.fixture
def crm(client):
    client.post("/admin/login", data=ADMIN)
    return client


def test_hidden_product_cannot_be_ordered(client, crm, db_session):
    product_id = client.get("/api/v1/products/soft-modal").json()["id"]
    target = variant_id(db_session, "SMD-BLU-M")
    crm.post(f"/admin/products/{product_id}/visibility")

    response = client.post("/api/v1/orders", json={**ORDER, "items": [{"variant_id": target, "quantity": 1}]})
    assert response.status_code == 422


def test_free_products_cannot_be_created(crm):
    response = crm.post("/admin/products", data={
        "name": "Zero", "slug": "zero-price", "description": "x", "material": "x", "image_url": "",
        "sku": "ZRO-1", "size": "M", "color": "Black", "price": "0", "stock": "5",
    }, follow_redirects=False)
    assert response.status_code == 422


def test_variants_cannot_be_added_with_negative_stock(crm, client):
    product_id = client.get("/api/v1/products/everyday-cotton").json()["id"]
    response = crm.post(f"/admin/products/{product_id}/variants", data={"sku": "EDC-BLK-XS", "size": "XS", "color": "Black", "price": "590", "stock": "-1"}, follow_redirects=False)
    assert response.status_code == 422


def test_birth_date_cannot_be_in_the_future(client, customer_token):
    response = client.patch("/api/v1/account", headers={"Authorization": f"Bearer {customer_token}"}, json={"birth_date": "2090-01-01"})
    assert response.status_code == 422


def test_past_birth_date_is_accepted(client, customer_token):
    response = client.patch("/api/v1/account", headers={"Authorization": f"Bearer {customer_token}"}, json={"birth_date": "1995-04-17"})
    assert response.status_code == 200


def test_basket_size_is_capped(client, db_session):
    line = {"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 1}
    assert client.post("/api/v1/orders", json={**ORDER, "items": [line] * 21}).status_code == 422


def test_delivery_address_cannot_be_a_wall_of_text(client, db_session):
    response = client.post("/api/v1/orders", json={
        **ORDER, "delivery_address": "x" * 501,
        "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 1}],
    })
    assert response.status_code == 422


def test_profile_login_still_works_after_validation(client):
    assert client.post("/api/v1/auth/customer/login", json=CUSTOMER).status_code == 200
