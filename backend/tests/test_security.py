"""Tokens for shoppers and tokens for staff must never be interchangeable."""
from conftest import ADMIN, CUSTOMER, variant_id

from app.models import Customer, User
from app.security import create_customer_token, create_token

ORDER = {"email": "shopper@briefs.store", "name": "Shopper", "delivery_address": "Kyiv, Nova Poshta 1"}


def staff_and_customer_sharing_an_id(db_session) -> str:
    """A customer token whose id matches an existing staff member — the dangerous case."""
    with db_session() as session:
        staff = session.query(User).filter(User.email == ADMIN["email"]).one()
        customer = session.query(Customer).filter(Customer.email == CUSTOMER["email"]).one()
        customer.id = staff.id
        session.commit()
        return create_customer_token(customer)


def test_customer_token_cannot_read_orders(client, db_session):
    order_id = client.post("/api/v1/orders", json={**ORDER, "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 1}]}).json()["id"]
    token = staff_and_customer_sharing_an_id(db_session)

    assert client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_customer_token_cannot_open_the_crm(client, db_session):
    token = staff_and_customer_sharing_an_id(db_session)
    client.cookies.set("crm_token", token)

    for page in ["/admin", "/admin/orders", "/admin/products"]:
        response = client.get(page, follow_redirects=False)
        assert response.status_code == 303, page
    client.cookies.clear()


def test_customer_token_cannot_change_prices(client, db_session):
    token = staff_and_customer_sharing_an_id(db_session)
    target = variant_id(db_session, "EDC-BLK-M")
    client.cookies.set("crm_token", token)

    response = client.patch(f"/admin/variants/{target}", data={"price": "1", "stock": "0"}, follow_redirects=False)
    assert response.status_code == 303
    client.cookies.clear()

    from conftest import stock_of
    assert stock_of(db_session, "EDC-BLK-M") == 5


def test_staff_token_cannot_read_a_customer_profile(client, db_session):
    with db_session() as session:
        staff = session.query(User).filter(User.email == ADMIN["email"]).one()
        token = create_token(staff)

    assert client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_staff_token_still_works_for_staff_endpoints(client, db_session, admin_token):
    order_id = client.post("/api/v1/orders", json={**ORDER, "items": [{"variant_id": variant_id(db_session, "EDC-BLK-M"), "quantity": 1}]}).json()["id"]
    assert client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
