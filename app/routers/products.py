from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate


router = APIRouter(prefix="/products", tags=["products"])

DbSession = Annotated[Session, Depends(get_db)]


def get_product_or_404(product_id: int, db: DbSession) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


ProductDep = Annotated[Product, Depends(get_product_or_404)]


@router.get("")
def get_products(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: str | None = None,
):
    stmt = select(Product)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    products = db.scalars(stmt.order_by(Product.id).limit(limit).offset(offset)).all()

    return {
        "message": "Products received successfully",
        "data": [ProductRead.model_validate(p) for p in products],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/{product_id}")
def get_product(product: ProductDep):

    return {
        "message": "product found successfully",
        "data": ProductRead.model_validate(product),
    }


@router.post("", status_code=201)
def create_product(product: ProductCreate, db: DbSession):

    db_product = Product(**product.model_dump())
    db.add(db_product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A product with SKU Already exists")
    db.refresh(db_product)

    return {
        "message": "product added successfully",
        "data": ProductRead.model_validate(db_product),
    }


@router.patch("/{product_id}")
def update_product(changes: ProductUpdate, product: ProductDep, db: DbSession):

    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A product with SKU Already exists")
    db.refresh(product)

    return {
        "message": "product updated successfully",
        "data": ProductRead.model_validate(product),
    }


@router.delete("/{product_id}", status_code=204)
def delete_product(db: DbSession, product: ProductDep):

    db.delete(product)
    db.commit()
