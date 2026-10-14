from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus


def mark_payment_successful(
    db: Session, *, reference: str, amount_pesewas: int, currency: str
) -> None:
    payment = db.scalar(
        select(Payment).where(Payment.reference == reference).with_for_update()
    )
    if payment is None:
        return  # not one of ours

    if payment.status == PaymentStatus.SUCCESS:
        return  # already processed: idempotency

    if amount_pesewas != payment.amount_pesewas or currency != payment.currency:
        payment.status = PaymentStatus.FAILED
        db.commit()
        return

    order = db.scalar(
        select(Order).where(Order.id == payment.order_id).with_for_update()
    )
    if order is None:
        return
    payment.status = PaymentStatus.SUCCESS
    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PAID
    # If the order was cancelled while the customer was paying, the payment
    # still succeeded and must be refunded. We'll handle refunds later.

    db.commit()
