def add_to_cart(client, headers, product, quantity):
    response = client.post(
        "/cart/items",
        json={"product_id": product.id, "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 200


def test_checkout_creates_order_reduces_stock_and_empties_cart(
    client, db, customer_headers, product
):
    add_to_cart(client, customer_headers, product, 2)

    response = client.post("/orders", headers=customer_headers)

    assert response.status_code == 201
    order = response.json()["data"]
    assert order["status"] == "pending"
    assert order["total_pesewas"] == 2 * 5000

    cart = client.get("/cart", headers=customer_headers).json()["data"]
    assert cart["items"] == []

    db.refresh(product)
    assert product.stock == 1


def test_failed_checkout_changes_nothing(client, db, customer_headers, product):
    add_to_cart(client, customer_headers, product, 2)
    product.stock = 1  # someone else bought one in the meantime
    db.commit()

    response = client.post("/orders", headers=customer_headers)

    assert response.status_code == 409
    cart = client.get("/cart", headers=customer_headers).json()["data"]
    assert len(cart["items"]) == 1  # cart NOT emptied
    db.refresh(product)
    assert product.stock == 1  # stock NOT reduced


def test_cancelling_order_restores_stock(client, db, customer_headers, product):
    # Add 2 items to the cart
    add_to_cart(client, customer_headers, product, 2)

    # Check out
    checkout_response = client.post("/orders", headers=customer_headers)
    assert checkout_response.status_code == 201

    order = checkout_response.json()["data"]
    order_id = order["id"]

    # Stock should now be 1
    db.refresh(product)
    assert product.stock == 1

    # Cancel the order
    response = client.post(
        f"/orders/{order_id}/cancel",
        headers=customer_headers,
    )

    assert response.status_code == 200

    # Stock should be restored to 3
    db.refresh(product)
    assert product.stock == 3


def test_customer_cannot_cancel_order_twice(client, customer_headers, product):
    add_to_cart(client, customer_headers, product, 2)

    checkout_response = client.post("/orders", headers=customer_headers)
    assert checkout_response.status_code == 201

    order_id = checkout_response.json()["data"]["id"]

    # First cancellation should succeed
    first_response = client.post(
        f"/orders/{order_id}/cancel",
        headers=customer_headers,
    )
    assert first_response.status_code == 200

    # Second cancellation should fail
    second_response = client.post(
        f"/orders/{order_id}/cancel",
        headers=customer_headers,
    )
    assert second_response.status_code == 409


def test_customer_cannot_view_another_customers_order(
    client, customer_headers, other_customer_headers, product
):
    # Ama adds a product and checks out
    add_to_cart(client, customer_headers, product, 2)

    checkout_response = client.post("/orders", headers=customer_headers)
    assert checkout_response.status_code == 201

    order_id = checkout_response.json()["data"]["id"]

    # Kofi tries to access Ama's order
    response = client.get(
        f"/orders/{order_id}",
        headers=other_customer_headers,
    )

    assert response.status_code == 404
