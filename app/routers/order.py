import secrets
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser
from app.db.deps import DbSession
from app.models.cart import CartItem
from app.models.order import Order, OrderStatus, OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.schemas.order import OrderRead
from app.services.paystack import PaystackError, initialize_transaction

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_or_404(user: CurrentUser, db: DbSession, order_id: int) -> Order:
    order = db.scalar(
        select(Order).where(Order.user_id == user.id, Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


OrderDep = Annotated[Order, Depends(get_order_or_404)]


@router.get("")
def get_orders(user: CurrentUser, db: DbSession):
    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    ).all()

    return {
        "message": "Orders fetched successfully",
        "data": [OrderRead.model_validate(order) for order in orders],
    }


@router.get("/{order_id}")
def get_order(order: OrderDep):

    return {
        "message": "Order found Successfully",
        "data": OrderRead.model_validate(order),
    }


@router.post("", status_code=201)
def checkout(user: CurrentUser, db: DbSession):
    cart_items = db.scalars(select(CartItem).where(CartItem.user_id == user.id)).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    product_ids = [item.product_id for item in cart_items]
    products = db.scalars(
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
    ).all()
    products_by_id = {product.id: product for product in products}

    order = Order(user_id=user.id, status=OrderStatus.PENDING, total_pesewas=0)

    for item in cart_items:
        product = products_by_id[item.product_id]

        if item.quantity > product.stock:
            raise HTTPException(
                status_code=409,
                detail=f"Only {product.stock} of '{product.name}' left in stock",
            )

        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                unit_price_pesewas=product.price_pesewas,
                quantity=item.quantity,
            )
        )

        order.total_pesewas += item.quantity * product.price_pesewas
        product.stock -= item.quantity
        db.delete(item)

    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "message": "order placed successfully",
        "data": OrderRead.model_validate(order),
    }


@router.post("/{order_id}/cancel")
def cancel_order(order: OrderDep, db: DbSession):
    print("Print", order.status)
    db.refresh(order, with_for_update=True)
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=409, detail="Only pending orders can be cancelled"
        )
    order_items = order.items
    product_ids = [
        item.product_id for item in order_items if item.product_id is not None
    ]

    products = db.scalars(
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
    ).all()

    products_by_id = {product.id: product for product in products}
    for item in order_items:
        if item.product_id is None:
            continue

        product = products_by_id[item.product_id]

        product.stock += item.quantity

    order.status = OrderStatus.CANCELLED
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "message": "Order cancelled successfully",
        "order": OrderRead.model_validate(order),
    }


@router.post("{order_id}/pay")
def pay_for_order(order: OrderDep, user: CurrentUser, db: DbSession):
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="Only pending orders can be paind")
    reference = f"ord{order.id}-{secrets.token_hex(8)}"

    try:
        authorization_url = initialize_transaction(
            email=user.email,
            amount_pesewas=order.total_pesewas,
            reference=reference,
            order_id=order.id,
        )
    except PaystackError:
        raise HTTPException(
            status_code=502, detail="Payment provider unavailable, please try again"
        )

    db.add(
        Payment(
            order_id=order.id,
            reference=reference,
            amount_pesewas=order.total_pesewas,
        )
    )
    db.commit()

    return {
        "message": "payment initialized",
        "data": {"authorization_url": authorization_url, "reference": reference},
    }
