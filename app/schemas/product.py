from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    price_pesewas: int
    stock: int = 0



