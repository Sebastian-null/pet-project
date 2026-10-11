"""Checks for the attack surface: uploads, odd URLs and response headers."""
import pytest
from conftest import ADMIN

HTML_PRETENDING_TO_BE_PNG = b"<html><script>alert(1)</script></html>"
REAL_PNG = bytes.fromhex("89504e470d0a1a0a") + b"rest of a tiny png"


@pytest.fixture
def crm(client):
    client.post("/admin/login", data=ADMIN)
    return client


def test_avatar_upload_checks_the_file_itself_not_its_label(client, customer_token):
    response = client.post(
        "/api/v1/account/avatar",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"file": ("innocent.png", HTML_PRETENDING_TO_BE_PNG, "image/png")},
    )
    assert response.status_code == 415


def test_a_real_image_is_still_accepted(client, customer_token):
    response = client.post(
        "/api/v1/account/avatar",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"file": ("avatar.png", REAL_PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["avatar_url"].endswith(".png")


def test_product_photo_upload_checks_the_file_itself(crm, client):
    product_id = client.get("/api/v1/products/everyday-cotton").json()["id"]
    response = crm.post(
        f"/admin/products/{product_id}/image",
        files={"file": ("innocent.png", HTML_PRETENDING_TO_BE_PNG, "image/png")},
        follow_redirects=False,
    )
    assert response.status_code == 415


def test_strange_slugs_are_rejected_instead_of_crashing(client):
    for slug in ["%00", "../../etc/passwd", "everyday-cotton'; drop table products;--", "Everyday Cotton"]:
        assert client.get(f"/api/v1/products/{slug}").status_code in {404, 422}, slug


def test_search_survives_injection_attempts(client):
    for payload in ["' OR 1=1--", "'; DROP TABLE orders;--", "%' UNION SELECT NULL--"]:
        assert client.get("/api/v1/products", params={"q": payload}).status_code == 200
    assert len(client.get("/api/v1/products").json()) == 2


def test_responses_carry_protective_headers(client):
    headers = client.get("/api/v1/products").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"


def test_oversized_requests_are_refused_early(client):
    response = client.post(
        "/api/v1/orders",
        headers={"Content-Type": "application/json", "Content-Length": str(20 * 1024 * 1024)},
        content=b'{"items": []}',
    )
    assert response.status_code == 413
