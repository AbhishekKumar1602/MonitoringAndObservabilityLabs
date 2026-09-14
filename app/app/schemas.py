from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrderStatus = Literal["pending", "paid", "shipped", "cancelled"]


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    product: str = Field(min_length=1, max_length=160)
    quantity: int = Field(ge=1, le=10_000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    status: OrderStatus = "pending"


class OrderUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1, max_length=120)
    product: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: int | None = Field(default=None, ge=1, le=10_000)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: OrderStatus | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    product: str
    quantity: int
    unit_price: Decimal
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class DependencyStatus(BaseModel):
    status: Literal["ok", "error"]
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, DependencyStatus]
