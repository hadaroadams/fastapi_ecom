from fastapi import APIRouter, HTTPException
from app.schemas.product import ProductCreate


product_db: list[dict] = []

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def get_products():
    return {"message": "product fetched successfully", "data": product_db}


@router.get("/{product_id}")
def get_product(product_id: int):
    for product in product_db:
        if product["id"] == product_id:
            return {"message": "product found successfully", "data": product}

    raise HTTPException(status_code=404, detail="product not found")


@router.post("", status_code=201)
def create_product(product: ProductCreate):
    new_product = {"id": len(product_db) + 1, **product.model_dump()}
    product_db.append(new_product)
    return {"message": "product added successfully", "data": new_product}
