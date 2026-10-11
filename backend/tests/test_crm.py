import pytest
from conftest import ADMIN, stock_of

NEW_PRODUCT = {
    "name": "Linen Boxer", "slug": "linen-boxer", "description": "Breathable linen", "material": "linen",
    "image_url": "", "sku": "LIN-WHT-M", "size": "M", "color": "White", "price": "690", "stock": "4",
}


@pytest.fixture
def crm(client):
    client.post("/admin/login", data=ADMIN)
    return client


def test_crm_pages_send_guests_to_the_login_form(client):
    for page in ["/admin", "/admin/orders", "/admin/products"]:
        response = client.get(page, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login"


def test_api_still_answers_with_401(client):
    assert client.get("/api/v1/account").status_code == 401


def test_manager_can_publish_a_product(crm, client):
    response = crm.post("/admin/products", data=NEW_PRODUCT)
    assert response.status_code == 200  # redirect followed to the product list
    assert "Linen Boxer" in response.text

    storefront = client.get("/api/v1/products/linen-boxer")
    assert storefront.status_code == 200
    assert storefront.json()["variants"][0]["stock"] == 4


def test_duplicate_slug_is_reported_not_crashed(crm):
    crm.post("/admin/products", data=NEW_PRODUCT)
    response = crm.post("/admin/products", data={**NEW_PRODUCT, "sku": "LIN-WHT-L"}, follow_redirects=False)
    assert response.status_code == 409
    assert "already taken" in response.text


def test_manager_can_add_a_variant(crm, client, db_session):
    product_id = client.get("/api/v1/products/everyday-cotton").json()["id"]
    response = crm.post(f"/admin/products/{product_id}/variants", data={"sku": "EDC-BLK-S", "size": "S", "color": "Black", "price": "590", "stock": "7"})
    assert response.status_code == 200
    assert stock_of(db_session, "EDC-BLK-S") == 7


def test_duplicate_size_and_colour_is_refused(crm, client):
    product_id = client.get("/api/v1/products/everyday-cotton").json()["id"]
    response = crm.post(f"/admin/products/{product_id}/variants", data={"sku": "EDC-BLK-M2", "size": "M", "color": "Black", "price": "590", "stock": "1"}, follow_redirects=False)
    assert response.status_code == 409


def test_price_and_stock_can_be_corrected(crm, client, db_session):
    from conftest import variant_id
    target = variant_id(db_session, "EDC-BLK-M")

    response = crm.patch(f"/admin/variants/{target}", data={"price": "640.50", "stock": "12"})
    assert response.status_code == 200
    assert stock_of(db_session, "EDC-BLK-M") == 12
    variants = client.get("/api/v1/products/everyday-cotton").json()["variants"]
    assert next(variant["price"] for variant in variants if variant["sku"] == "EDC-BLK-M") == 640.5


def test_negative_stock_is_refused(crm, db_session):
    from conftest import variant_id
    target = variant_id(db_session, "EDC-BLK-M")
    assert crm.patch(f"/admin/variants/{target}", data={"price": "590", "stock": "-3"}).status_code == 422


def test_hidden_product_disappears_from_the_storefront(crm, client):
    product_id = client.get("/api/v1/products/soft-modal").json()["id"]
    crm.post(f"/admin/products/{product_id}/visibility")
    assert client.get("/api/v1/products/soft-modal").status_code == 404
