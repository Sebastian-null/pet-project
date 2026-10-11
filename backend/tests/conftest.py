import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import Customer, Gender, Product, Role, User, Variant
from app.security import password_hash

ADMIN = {"email": "admin@briefs.store", "password": "admin-secret"}
CUSTOMER = {"email": "customer@briefs.store", "password": "customer-secret"}
# Tests run on PostgreSQL because the app relies on row locking and timezone-aware
# timestamps, both of which SQLite silently ignores.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://briefs:briefs_dev_password@postgres:5432/briefs_test")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Tests never reach Stripe or a mail server; payment tests opt in per case."""
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "stripe_secret_key", None)
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret")


@pytest.fixture(autouse=True)
def forget_throttling():
    """Attempt counters live in module state, so each test starts from zero."""
    from app import throttling
    throttling._attempts.clear()
    yield
    throttling._attempts.clear()


@pytest.fixture
def sent_codes(monkeypatch) -> list[tuple[str, str]]:
    delivered: list[tuple[str, str]] = []
    monkeypatch.setattr("app.api.send_verification_code", lambda email, code: delivered.append((email, code)))
    return delivered


@pytest.fixture(scope="session")
def engine():
    base_url, database = TEST_DATABASE_URL.rsplit("/", 1)
    maintenance = create_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
    with maintenance.connect() as connection:
        if not connection.scalar(text("select 1 from pg_database where datname = :name"), {"name": database}):
            connection.execute(text(f'create database "{database}"'))
    maintenance.dispose()

    test_engine = create_engine(TEST_DATABASE_URL)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        session.add(User(email=ADMIN["email"], password_hash=password_hash(ADMIN["password"]), role=Role.ADMIN))
        session.add(Customer(email=CUSTOMER["email"], name="Test Customer", password_hash=password_hash(CUSTOMER["password"])))
        cotton = Product(slug="everyday-cotton", name="Everyday Cotton", description="Soft briefs", material="cotton", image_url=None, gender=Gender.MEN, category="briefs")
        cotton.variants = [
            Variant(sku="EDC-BLK-M", size="M", color="Black", price=590, stock=5),
            Variant(sku="EDC-BLK-L", size="L", color="Black", price=590, stock=0),
        ]
        modal = Product(slug="soft-modal", name="Soft Modal", description="Smooth modal", material="modal", image_url=None, gender=Gender.WOMEN, category="bra")
        modal.variants = [Variant(sku="SMD-BLU-M", size="M", color="Blue", price=790, stock=3)]
        session.add_all([cotton, modal])
        session.commit()
    yield session_factory


@pytest.fixture
def client(db_session):
    def override_get_db():
        session = db_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def customer_token(client) -> str:
    response = client.post("/api/v1/auth/customer/login", json=CUSTOMER)
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client) -> str:
    response = client.post("/api/v1/auth/login", json=ADMIN)
    return response.json()["access_token"]


def variant_id(db_session, sku: str) -> int:
    with db_session() as session:
        return session.query(Variant).filter(Variant.sku == sku).one().id


def stock_of(db_session, sku: str) -> int:
    with db_session() as session:
        return session.query(Variant).filter(Variant.sku == sku).one().stock
