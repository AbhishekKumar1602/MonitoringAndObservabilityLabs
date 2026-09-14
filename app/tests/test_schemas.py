from decimal import Decimal

import pytest
from app.schemas import OrderCreate
from pydantic import ValidationError


def test_order_create_accepts_valid_payload() -> None:
    order = OrderCreate(
        customer_name="Ada Lovelace",
        product="Telemetry Handbook",
        quantity=2,
        unit_price=Decimal("19.95"),
    )
    assert order.quantity == 2
    assert order.status == "pending"


def test_order_create_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        OrderCreate(
            customer_name="Ada Lovelace",
            product="Telemetry Handbook",
            quantity=0,
            unit_price=Decimal("19.95"),
        )
