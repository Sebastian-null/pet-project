from conftest import ADMIN, CUSTOMER

from app.throttling import ATTEMPT_LIMIT


def wrong_login(client, email: str = CUSTOMER["email"]):
    return client.post("/api/v1/auth/customer/login", json={"email": email, "password": "wrong-password"})


def test_password_guessing_is_cut_off(client):
    for _ in range(ATTEMPT_LIMIT):
        assert wrong_login(client).status_code == 401

    blocked = wrong_login(client)
    assert blocked.status_code == 429
    assert "Too many attempts" in blocked.json()["detail"]

    # Even the real password is refused while the lockout lasts.
    assert client.post("/api/v1/auth/customer/login", json=CUSTOMER).status_code == 429


def test_a_successful_login_clears_the_counter(client):
    for _ in range(ATTEMPT_LIMIT - 1):
        wrong_login(client)
    assert client.post("/api/v1/auth/customer/login", json=CUSTOMER).status_code == 200

    for _ in range(ATTEMPT_LIMIT - 1):
        assert wrong_login(client).status_code == 401


def test_lockout_is_per_account(client):
    for _ in range(ATTEMPT_LIMIT + 1):
        wrong_login(client, "someone-else@briefs.store")
    assert client.post("/api/v1/auth/customer/login", json=CUSTOMER).status_code == 200


def test_admin_login_is_protected_too(client):
    for _ in range(ATTEMPT_LIMIT):
        client.post("/api/v1/auth/login", json={"email": ADMIN["email"], "password": "wrong"})
    assert client.post("/api/v1/auth/login", json=ADMIN).status_code == 429


def test_code_requests_cannot_be_spammed(client, sent_codes):
    for index in range(ATTEMPT_LIMIT):
        response = client.post("/api/v1/auth/register/request-code", json={"email": f"buyer{index}@briefs.store", "name": "Buyer", "password": "Sup3rSecret!"})
        assert response.status_code == 202

    flood = client.post("/api/v1/auth/register/request-code", json={"email": "one-too-many@briefs.store", "name": "Buyer", "password": "Sup3rSecret!"})
    assert flood.status_code == 429
