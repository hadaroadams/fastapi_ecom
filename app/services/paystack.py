import logging
import hashlib
import hmac

import httpx

from app.core.config import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def _header() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.paystack_secret_key}"}


logger = logging.getLogger(__name__)


def _request(method: str, path: str, **kwargs) -> dict:
    try:
        response = httpx.request(
            method,
            f"{PAYSTACK_BASE_URL}{path}",
            headers=_header(),
            timeout=10,
            **kwargs,
        )
    except httpx.RequestError as exc:
        # We never got an answer: no network, DNS failure, timeout.
        logger.error("Paystack unreachable on %s: %s", path, exc)
        raise PaystackError("Could not reach Paystack") from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.is_error or not body.get("status"):
        # Paystack answered, but said no.
        logger.error(
            "Paystack error %s on %s: %s",
            response.status_code,
            path,
            body.get("message"),
        )
        raise PaystackError(body.get("message", "Paystack error"))

    return body["data"]


def initialize_transaction(
    *, email: str, amount_pesewas: int, reference: str, order_id: int
) -> str:
    data = _request(
        "POST",
        "/transaction/initialize",
        json={
            "email": email,
            "amount": amount_pesewas,
            "currency": "GHS",
            "reference": reference,
            "callback_url": settings.paystack_callback_url,
            "channels": ["card", "mobile_money"],
            "metadata": {"order_id": order_id},
        },
    )
    paystack_reference = data["reference"]
    # authorization_url = data["authorization_url"]

    print("Generated reference:", reference)
    print("Paystack reference:", paystack_reference)
    return data["authorization_url"]


def verify_transaction(reference: str) -> dict:
    return _request("GET", f"/transaction/verify/{reference}")


def is_valid_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(
        settings.paystack_secret_key.encode(), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
