from conftest import CUSTOMER

NEW_PASSWORD = "Even-Better-Secret-1"


def change(client, token: str, current: str, new: str = NEW_PASSWORD):
    return client.post(
        "/api/v1/account/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": current, "new_password": new},
    )


def test_password_change_requires_a_token(client):
    assert client.post("/api/v1/account/password", json={"current_password": "a", "new_password": "b" * 10}).status_code == 401


def test_wrong_current_password_is_refused(client, customer_token):
    assert change(client, customer_token, "not-my-password").status_code == 401


def test_short_passwords_are_refused(client, customer_token):
    assert change(client, customer_token, CUSTOMER["password"], "short").status_code == 422


def test_customer_can_change_password_and_sign_in_with_it(client, customer_token):
    assert change(client, customer_token, CUSTOMER["password"]).status_code == 204

    assert client.post("/api/v1/auth/customer/login", json={"email": CUSTOMER["email"], "password": CUSTOMER["password"]}).status_code == 401
    assert client.post("/api/v1/auth/customer/login", json={"email": CUSTOMER["email"], "password": NEW_PASSWORD}).status_code == 200


def test_guest_without_a_password_is_told_to_register(client, db_session, customer_token):
    from app.models import Customer
    with db_session() as session:
        guest = session.query(Customer).filter(Customer.email == CUSTOMER["email"]).one()
        guest.password_hash = None
        session.commit()

    assert change(client, customer_token, "anything").status_code == 409
