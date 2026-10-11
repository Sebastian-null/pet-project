"""Regressions for holes found during the security pass.

The central one: guest checkout used to look a customer up by the email typed into
the form and then overwrite that row, so anyone could edit a registered shopper's
details and drop orders into their account without ever signing in.
"""
from conftest import CUSTOMER, variant_id

from app.models import Customer

GUEST = {"email": "walk-in@briefs.store", "name": "Walk In", "phone": "+380670000000", "delivery_address": "Kyiv, Nova Poshta 1"}
ATTACK = {"email": CUSTOMER["email"], "name": "Overwritten", "phone": "+000000000000", "delivery_address": "Attacker address 12345"}


def order(client, db_session, form: dict, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/v1/orders", headers=headers, json={**form, "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 1}]})


def profile(db_session, email: str) -> Customer:
    with db_session() as session:
        return session.query(Customer).filter(Customer.email == email).one()


def test_guest_cannot_check_out_under_a_registered_email(client, db_session):
    assert order(client, db_session, ATTACK).status_code == 401


def test_a_refused_takeover_leaves_the_profile_untouched(client, db_session):
    before = profile(db_session, CUSTOMER["email"])
    name, phone = before.name, before.phone

    order(client, db_session, ATTACK)

    after = profile(db_session, CUSTOMER["email"])
    assert (after.name, after.phone) == (name, phone)


def test_a_refused_takeover_creates_no_order_and_holds_no_stock(client, db_session):
    from conftest import stock_of
    order(client, db_session, ATTACK)

    assert stock_of(db_session, "EDC-BLK-M") == 5
    with db_session() as session:
        assert session.query(Customer).filter(Customer.email == CUSTOMER["email"]).one().orders == []


def test_the_owner_can_still_order_with_their_own_email(client, db_session, customer_token):
    assert order(client, db_session, ATTACK, token=customer_token).status_code == 201


def test_guest_checkout_still_works_for_a_new_email(client, db_session):
    assert order(client, db_session, GUEST).status_code == 201


def test_a_returning_guest_is_still_matched_by_email(client, db_session):
    order(client, db_session, GUEST)
    order(client, db_session, GUEST)
    with db_session() as session:
        assert session.query(Customer).filter(Customer.email == GUEST["email"]).count() == 1


def test_registration_refuses_a_weak_password(client, sent_codes):
    response = client.post("/api/v1/auth/register/request-code", json={"email": "weak@briefs.store", "name": "Weak", "password": "1"})
    assert response.status_code == 422
    assert sent_codes == []


def test_registration_accepts_a_strong_password(client, sent_codes):
    response = client.post("/api/v1/auth/register/request-code", json={"email": "strong@briefs.store", "name": "Strong", "password": "Sup3rSecret!"})
    assert response.status_code == 202


def test_clearing_the_name_is_a_validation_error_not_a_crash(client, customer_token):
    response = client.patch("/api/v1/account", headers={"Authorization": f"Bearer {customer_token}"}, json={"name": None})
    assert response.status_code == 422


def test_nullable_profile_fields_can_still_be_cleared(client, customer_token):
    response = client.patch("/api/v1/account", headers={"Authorization": f"Bearer {customer_token}"}, json={"phone": None, "birth_date": None})
    assert response.status_code == 200
    assert response.json()["phone"] is None


def test_a_token_with_no_subject_is_refused(client):
    import jwt

    from app.config import settings
    forged = jwt.encode({"kind": "customer"}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert client.get("/api/v1/account", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_a_product_image_url_the_storefront_cannot_render_is_refused(client, db_session):
    from conftest import ADMIN
    client.post("/admin/login", data=ADMIN)
    response = client.post("/admin/products", data={
        "name": "Elsewhere", "slug": "elsewhere", "description": "x", "material": "x",
        "image_url": "https://evil.example.org/tracker.png",
        "sku": "ELS-1", "size": "M", "color": "Black", "price": "590", "stock": "5",
    }, follow_redirects=False)
    assert response.status_code == 422
