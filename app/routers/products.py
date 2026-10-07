from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.product import ProductCreate, ProductRead

from app.db.session import get_db
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.product import Product


# product_db: list[dict] = []

router = APIRouter(prefix="/products", tags=["products"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def get_products(db: DbSession):
    products = db.scalars(select(Product)).all()

    return {
        "message": "Products received successfully",
        # "data": products,
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
    db.commit()
    db.refresh(db_product)
    return {
        "message": "product added successfully",
        "data": ProductRead.model_validate(db_product),
    }
