from conftest import CUSTOMER

NEW_ACCOUNT = {"email": "buyer@briefs.store", "name": "New Buyer", "password": "Sup3rSecret!"}


def register(client, sent_codes) -> str:
    client.post("/api/v1/auth/register/request-code", json=NEW_ACCOUNT)
    return sent_codes[-1][1]


def test_registration_emails_a_six_digit_code(client, sent_codes):
    response = client.post("/api/v1/auth/register/request-code", json=NEW_ACCOUNT)
    assert response.status_code == 202
    recipient, code = sent_codes[-1]
    assert recipient == NEW_ACCOUNT["email"]
    assert len(code) == 6 and code.isdigit()


def test_wrong_code_is_rejected(client, sent_codes):
    register(client, sent_codes)
    response = client.post("/api/v1/auth/register/confirm", json={"email": NEW_ACCOUNT["email"], "code": "000000"})
    assert response.status_code == 400


def test_correct_code_creates_the_account(client, sent_codes):
    code = register(client, sent_codes)
    response = client.post("/api/v1/auth/register/confirm", json={"email": NEW_ACCOUNT["email"], "code": code})
    assert response.status_code == 201
    assert response.json()["email"] == NEW_ACCOUNT["email"]

    login = client.post("/api/v1/auth/customer/login", json={"email": NEW_ACCOUNT["email"], "password": NEW_ACCOUNT["password"]})
    assert login.status_code == 200


def test_code_works_only_once(client, sent_codes):
    code = register(client, sent_codes)
    client.post("/api/v1/auth/register/confirm", json={"email": NEW_ACCOUNT["email"], "code": code})
    repeated = client.post("/api/v1/auth/register/confirm", json={"email": NEW_ACCOUNT["email"], "code": code})
    assert repeated.status_code == 400


def test_existing_email_cannot_register_again(client, sent_codes):
    response = client.post("/api/v1/auth/register/request-code", json={**NEW_ACCOUNT, "email": CUSTOMER["email"]})
    assert response.status_code == 409


def test_login_rejects_a_wrong_password(client):
    response = client.post("/api/v1/auth/customer/login", json={"email": CUSTOMER["email"], "password": "not-it"})
    assert response.status_code == 401


def test_profile_requires_a_token(client):
    assert client.get("/api/v1/account").status_code == 401


def test_profile_can_be_read_and_updated(client, customer_token):
    headers = {"Authorization": f"Bearer {customer_token}"}
    assert client.get("/api/v1/account", headers=headers).json()["email"] == CUSTOMER["email"]

    response = client.patch("/api/v1/account", headers=headers, json={"name": "Renamed", "birth_date": "1995-04-17"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["birth_date"] == "1995-04-17"


def test_avatar_rejects_files_that_are_not_images(client, customer_token):
    response = client.post(
        "/api/v1/account/avatar",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"file": ("note.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


def test_admin_token_is_issued_with_a_role(client, admin_token):
    assert admin_token
    response = client.post("/api/v1/auth/login", json={"email": "admin@briefs.store", "password": "wrong"})
    assert response.status_code == 401
