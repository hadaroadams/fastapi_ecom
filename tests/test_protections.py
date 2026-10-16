def test_security_headers_are_present(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_allows_the_configured_website(client):
    response = client.options(
        "/products",
        headers={
            "Origin": "https://shop.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] == "https://shop.example.com"


def test_cors_blocks_other_websites(client):
    response = client.options(
        "/products",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_login_is_rate_limited(client):
    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={"username": "x@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login", data={"username": "x@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 429
