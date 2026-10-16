def test_customer_can_get_empty_cart(client, customer_headers):
    response = client.get("/cart", headers=customer_headers)

    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


def test_customer_can_add_product_to_cart(client, product, customer_headers):
    response = client.post(
        "/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=customer_headers,
    )

    assert response.status_code in (200, 201)


def test_unauthenticated_user_cannot_get_cart(client):
    response = client.get("/cart")

    assert response.status_code == 401


def test_customer_can_remove_cart_item(client, product, customer_headers):
    client.post(
        "/cart/items",
        json={"quantity": 1, "product_id": product.id},
        headers=customer_headers,
    )
    response = client.delete(
        f"/cart/items/{product.id}",
        headers=customer_headers,
    )

    assert response.status_code == 204


def test_adding_same_product_twice_increases_quantity(
    client, product, customer_headers
):

    client.post(
        "/cart/items",
        json={"quantity": 2, "product_id": product.id},
        headers=customer_headers,
    )

    client.post(
        "/cart/items",
        json={"quantity": 1, "product_id": product.id},
        headers=customer_headers,
    )

    response = client.get("/cart", headers=customer_headers)

    assert response.status_code == 200

    items = response.json()["data"]["items"]

    assert len(items) == 1

    assert items[0]["quantity"] == 3


def test_customer_cannot_add_more_than_stock(client, product, customer_headers):
    response = client.post(
        "/cart/items",
        json={"quantity": 4, "product_id": product.id},
        headers=customer_headers,
    )

    assert response.status_code == 409


def test_customer_cannot_update_another_customers_cart(
    client, product, customer_headers, other_customer_headers
):
    # 1. Ama adds 2 units to her cart.
    add_response = client.post(
        "/cart/items",
        json={"quantity": 2, "product_id": product.id},
        headers=customer_headers,
    )
    assert add_response.status_code == 200

    # 2. Kofi tries to change Ama's cart item.
    update_response = client.patch(
        f"/cart/items/{product.id}",
        json={"quantity": 1},
        headers=other_customer_headers,
    )
    assert update_response.status_code == 404

    # 3. Confirm Ama's cart still contains quantity 2.
    cart_response = client.get("/cart", headers=customer_headers)

    assert cart_response.status_code == 200

    items = cart_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 2
