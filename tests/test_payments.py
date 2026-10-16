import hashlib
import hmac
import json

from app.core.config import settings
from app.models.order import Order


def fake_initialize_transaction(**kwargs):
    return "https://checkout.paystack.test/fake"


def test_pay_returns_a_payment_link(client, customer_headers, product, monkeypatch):
    monkeypatch.setattr(
        "app.routers.order.initialize_transaction",
        fake_initialize_transaction,
    )
    client.post(
        "/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=customer_headers,
    )
    order_id = client.post("/orders", headers=customer_headers).json()["data"]["id"]

    response = client.post(f"/orders/{order_id}/pay", headers=customer_headers)

    assert response.status_code == 200
    assert (
        response.json()["data"]["authorization_url"]
        == "https://checkout.paystack.test/fake"
    )


def sign(payload: bytes) -> str:
    return hmac.new(
        settings.paystack_secret_key.encode(), payload, hashlib.sha512
    ).hexdigest()


def test_signed_webhook_marks_order_paid(
    client, customer_headers, product, monkeypatch
):
    monkeypatch.setattr(
        "app.routers.order.initialize_transaction", fake_initialize_transaction
    )
    client.post(
        "/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=customer_headers,
    )
    order_id = client.post("/orders", headers=customer_headers).json()["data"]["id"]
    reference = client.post(f"/orders/{order_id}/pay", headers=customer_headers).json()[
        "data"
    ]["reference"]

    payload = json.dumps(
        {
            "event": "charge.success",
            "data": {"reference": reference, "amount": 5000, "currency": "GHS"},
        }
    ).encode()
    headers = {
        "x-paystack-signature": sign(payload),
        "Content-Type": "application/json",
    }

    response = client.post("/payments/webhook", content=payload, headers=headers)

    assert response.status_code == 200
    order = client.get(f"/orders/{order_id}", headers=customer_headers).json()["data"]
    assert order["status"] == "paid"


def start_payment(client, headers, product, monkeypatch):
    # Replace the real Paystack initialization with our fake.
    monkeypatch.setattr(
        "app.routers.order.initialize_transaction",
        fake_initialize_transaction,
    )

    # Add a product to the cart.
    cart_response = client.post(
        "/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 200

    # Create an order.
    order_response = client.post("/orders", headers=headers)
    assert order_response.status_code == 201

    order_id = order_response.json()["data"]["id"]

    # Initialize payment.
    payment_response = client.post(
        f"/orders/{order_id}/pay",
        headers=headers,
    )
    assert payment_response.status_code == 200

    payment_data = payment_response.json()["data"]
    reference = payment_data["reference"]

    return order_id, reference


def sign_payload(payload):
    body = json.dumps(payload).encode("utf-8")

    signature = hmac.new(
        settings.paystack_secret_key.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()

    return body, signature


def test_webhook_rejects_forged_signature(client):
    response = client.post(
        "/payments/webhook",
        json={},
        headers={"x-paystack-signature": "forged"},
    )

    assert response.status_code == 401


def test_wrong_webhook_amount_does_not_mark_order_paid(
    client, db, customer_headers, product, monkeypatch
):
    order_id, reference = start_payment(client, customer_headers, product, monkeypatch)

    payload = {
        "event": "charge.success",
        "data": {"reference": reference, "amount": 1, "currency": "GHS"},
    }

    body, signature = sign_payload(payload)

    response = client.post(
        "/payments/webhook",
        content=body,
        headers={
            "x-paystack-signature": signature,
            "content-type": "application/json",
        },
    )

    assert response.status_code == 200

    # Fetch the order again from the database.

    order = db.get(Order, order_id)
    db.refresh(order)

    assert order.status == "pending"


def test_same_webhook_twice_is_safe(client, db, customer_headers, product, monkeypatch):
    order_id, reference = start_payment(client, customer_headers, product, monkeypatch)

    # Use the expected amount for one item.
    payload = {
        "event": "charge.success",
        "data": {
            "reference": reference,
            "amount": product.price_pesewas,
            "currency": "GHS",
        },
    }

    body, signature = sign_payload(payload)
    headers = {
        "x-paystack-signature": signature,
        "content-type": "application/json",
    }

    first_response = client.post(
        "/payments/webhook",
        content=body,
        headers=headers,
    )
    second_response = client.post(
        "/payments/webhook",
        content=body,
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    from app.models.order import Order

    order = db.get(Order, order_id)
    db.refresh(order)

    assert order.status == "paid"


def test_paid_order_cannot_be_cancelled(client, customer_headers, product, monkeypatch):
    order_id, reference = start_payment(client, customer_headers, product, monkeypatch)
    body, signature = sign_payload(
        {
            "event": "charge.success",
            "data": {
                "reference": reference,
                "amount": product.price_pesewas,
                "currency": "GHS",
            },
        }
    )
    client.post(
        "/payments/webhook",
        content=body,
        headers={"x-paystack-signature": signature, "content-type": "application/json"},
    )

    response = client.post(f"/orders/{order_id}/cancel", headers=customer_headers)

    assert response.status_code == 409
