def test_get_product_by_id(client, product):
    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Black shirt"
    assert response.json()["data"]["stock"] == 3


def test_get_list_products(client, product):
    response = client.get("/products")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


def test_get_product_by_id_return_404(client):
    response = client.get(f"/products/99999")
    assert response.status_code == 404


def test_get_product_by_search_in_case_insensitive_upper_case(client, product):
    response = client.get(f"/products?search=SHIRT")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


def test_get_product_by_search_in_case_insensitive_lower_case(client, product):
    response = client.get(f"/products?search=hirt")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


def test_get_product_by_search_outside_search(client, product):
    response = client.get(f"/products?search=hat")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0


NEW_PRODUCT = {"name": "Hat", "sku": "HAT-1", "price_pesewas": 2000}


def test_admin_can_create_product(client, admin_headers):
    response = client.post("/products", json=NEW_PRODUCT, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["data"]["sku"] == "HAT-1"


def test_customer_cannot_create_product(client, customer_headers):
    response = client.post("/products", json=NEW_PRODUCT, headers=customer_headers)

    assert response.status_code == 403


NEGATIVE_PRICE_PRODUCT = {"name": "Hat", "sku": "HAT-1", "price_pesewas": -2000}


def test_admin_cannot_create_with_negetive_price(client, admin_headers):
    response = client.post(
        "/products", json=NEGATIVE_PRICE_PRODUCT, headers=admin_headers
    )
    assert response.status_code == 422


SAME_SKU_PRODUCT = {"name": "Hbat", "sku": "SHIRT-BLK", "price_pesewas": 2000}


def test_admin_cannot_create_product_with_same_sku(client, admin_headers, product):
    response = client.post("/products", json=SAME_SKU_PRODUCT, headers=admin_headers)
    assert response.status_code == 409
