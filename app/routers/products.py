from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate


router = APIRouter(prefix="/products", tags=["products"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def get_products(db: DbSession):
    products = db.scalars(select(Product)).all()

    return {
        "message": "Products received successfully",
        "data": [ProductRead.model_validate(product) for product in products],
    }


@router.get("/{product_id}")
def get_product(product_id: int, db: DbSession):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

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
def update_product(product_id: int, changes: ProductUpdate, db: DbSession):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

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
def delete_product(product_id: int, db: DbSession):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    db.delete(product)
    db.commit()
