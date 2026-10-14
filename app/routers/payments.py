import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.db.deps import DbSession
from app.models.order import Order
from app.models.payment import Payment, PaymentStatus
from app.services.payments import mark_payment_successful
from app.services.paystack import PaystackError, is_valid_signature, verify_transaction


router = APIRouter(prefix="/payments", tags=["payments"])


async def get_raw_body(request: Request) -> bytes:
    return await request.body()


@router.post("/webhook")
def paystack_webhook(
    db: DbSession,
    body: Annotated[bytes, Depends(get_raw_body)],
    x_paystack_signature: Annotated[str | None, Header()] = None,
):
    if not is_valid_signature(body, x_paystack_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(body)

    if event.get("event") == "charge.success":
        data = event["data"]
        mark_payment_successful(
            db,
            reference=data["reference"],
            amount_pesewas=data["amount"],
            currency=data["currency"],
        )

    return {"status": "ok"}


@router.get("/verify/{reference}")
def verify_payment(user: CurrentUser, db: DbSession, reference: str):
    payment = db.scalar(
        select(Payment).where(
            Payment.reference == reference,
            Payment.order.has(Order.user_id == user.id),
        )
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment or order not found")

    try:
        data = verify_transaction(reference=reference)

    except PaystackError as exc:
        print("Paystack verification failed:", repr(exc))

        raise HTTPException(
            status_code=502,
            detail="Payment provider unavailable, please try again",
        ) from exc

    if data["status"] == "success":
        mark_payment_successful(
            db,
            reference=reference,
            amount_pesewas=data["amount"],
            currency=data["currency"],
        )

    return {
        "message": "payment status retrieved",
        "data": {
            "paystack_status": data["status"],
            "payment_status": payment.status,
            "order_status": payment.order.status,
        },
    }
