from pydantic import Field, BaseModel, ConfigDict

from app.schemas.product import ProductRead


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=100)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product: ProductRead
    quantity: int
    line_total_pesewas: int


class CartRead(BaseModel):
    items: list[CartItemRead]
    total_pesewas: int
