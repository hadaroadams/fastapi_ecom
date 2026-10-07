from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    name: str
    price_pesewas: int
    stock: int = 0


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
