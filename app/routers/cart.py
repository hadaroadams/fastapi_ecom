from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser
from app.db.deps import DbSession
from app.models.cart import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemAdd, CartItemRead, CartItemUpdate, CartRead


router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_item_or_404(product_id: int, db: DbSession, user: CurrentUser) -> CartItem:
    cart_item = db.scalar(
        select(CartItem).where(
            CartItem.product_id == product_id, CartItem.user_id == user.id
        )
    )
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Item not in cart")
    return cart_item


CartItemDep = Annotated[CartItem, Depends(get_cart_item_or_404)]


@router.get("")
def get_cart(user: CurrentUser, db: DbSession):
    items = db.scalars(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == user.id)
        .order_by(CartItem.id)
    ).all()

    cart = CartRead(
        items=[CartItemRead.model_validate(item) for item in items],
        total_pesewas=sum(item.line_total_pesewas for item in items),
    )
    return {"message": "cart retrieved successfully", "data": cart}


@router.post("/items")
def add_to_cart(
    user: CurrentUser,
    db: DbSession,
    item_in: CartItemAdd,
):
    product = db.get(Product, item_in.product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product Not found")

    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product.id
        )
    )
    current_quantity = item.quantity if item else 0
    new_quantity = current_quantity + item_in.quantity

    if new_quantity > product.stock:
        raise HTTPException(status_code=409, detail=f"Only {product.stock} in stock")

    if item:
        item.quantity = new_quantity
    else:
        item = CartItem(user_id=user.id, product_id=product.id, quantity=new_quantity)
        db.add(item)

    db.commit()
    db.refresh(item)

    return {"message": "item added to cart", "data": CartItemRead.model_validate(item)}


@router.patch("/items/{product_id}")
def update_cart_item(
    db: DbSession,
    change: CartItemUpdate,
    cart_item: CartItemDep,
):

    if change.quantity > cart_item.product.stock:
        raise HTTPException(
            status_code=409, detail=f"Only {cart_item.product.stock} in stock"
        )

    cart_item.quantity = change.quantity
    db.commit()
    db.refresh(cart_item)

    return {
        "message": "cart item updated",
        "data": CartItemRead.model_validate(cart_item),
    }


@router.delete("/items/{product_id}", status_code=204)
def delete_cart_item(db: DbSession, cart_item: CartItemDep):

    db.delete(cart_item)
    db.commit()
