from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int | None
    product_name: str
    unit_price_pesewas: int
    quantity: int
    line_total_pesewas: int


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    total_pesewas: int
    created_at: datetime
    items: list[OrderItemRead]

