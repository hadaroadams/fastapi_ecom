from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health_check_return_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_welcome_check_return_app_name():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app_name"] == settings.app_name


def test_product_param_integer_value():
    response = client.get("/products/qwe")
    assert response.status_code == 422


def test_sign_up_fails_email_validation():
    response = client.post(
        "/auth/register",
        json={
            "email": "not_an_email",
            "password": "211231231",
            "full_name": "Hadaro Adams",
        },
    )
    assert response.status_code == 422


def test_create_product_return_401():
    response = client.post(
        "/products", json={"name": "Hat", "sku": "HAT_1", "price_pesewas": 2000}
    )
    assert response.status_code == 401


def test_sign_up_rejects_invalid_email():
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "full_name": "Ama Mensah",
            "password": "secret123",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]
