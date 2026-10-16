import os


# 1. Point the app at the TEST database. This must come before importing anything
#    from app, because the settings are read the moment app code is imported.
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://hadaroadams@localhost:5432/ecommerce_test"
)
os.environ["PAYSTACK_SECRET_KEY"] = "sk_test_fake_key_for_tests"
os.environ["DEBUG"] = "false"
os.environ["CORS_ORIGINS"] = '["https://shop.example.com"]'

from app.core.security import create_access_token, hash_password
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402, F401  (registers every table)
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import sessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.user import User
from app.core.rate_limit import limiter

# 2. Safety catch: never run tests against the real database.
assert "test" in settings.database_url, "Tests must use the test database!"


# 3. Create all tables once, when the test run starts. Drop them at the end.
@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


# 4. After EVERY test, empty every table, so the next test starts clean.
@pytest.fixture(autouse=True)
def clean_tables():
    yield
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


# 5. Something to send requests with.
@pytest.fixture
def client():
    return TestClient(app)


# 6. A database session, so tests can add data directly.
@pytest.fixture
def db():
    session = sessionLocal()
    yield session
    session.close()


# 7. A ready-made product with 3 in stock.
@pytest.fixture
def product(db):
    product = Product(name="Black shirt", sku="SHIRT-BLK", price_pesewas=5000, stock=3)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def create_user(db, email: str, is_admin: bool = False):
    user = User(
        email=email,
        full_name="Test User",
        hashed_password=hash_password("secret123"),
        is_admin=is_admin,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


# ----- user features -----
@pytest.fixture
def customer_headers(db):
    return auth_headers(create_user(db, "ama@example.com"))


@pytest.fixture
def other_customer_headers(db):
    return auth_headers(create_user(db, "kofi@example.com"))


@pytest.fixture
def admin_headers(db):
    return auth_headers(create_user(db, "admin@example.com", is_admin=True))


@pytest.fixture(autouse=True)
def reset_rate_limits():
    limiter.reset()

def test_security_headers_are_present(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_allows_the_configured_website(client):
    response = client.options(
        "/products",
        headers={"Origin": "https://shop.example.com", "Access-Control-Request-Method": "GET"},
    )

    assert response.headers["access-control-allow-origin"] == "https://shop.example.com"


def test_cors_blocks_other_websites(client):
    response = client.options(
        "/products",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers


def test_login_is_rate_limited(client):
    for _ in range(5):
        response = client.post("/auth/login", data={"username": "x@example.com", "password": "wrong-password"})
        assert response.status_code == 401

    response = client.post("/auth/login", data={"username": "x@example.com", "password": "wrong-password"})
    assert response.status_code == 429