import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.order import Order


class PaymentStatus(enum.StrEnum):
    INITIALIZED = "initialized"
    SUCCESS = "success"
    FAILED = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    amount_pesewas: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="GHS")
    status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.INITIALIZED)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship()
