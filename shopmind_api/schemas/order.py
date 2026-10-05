from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_number: SecretStr
    expiry_month: int = Field(strict=True)
    expiry_year: int = Field(strict=True)
    cvv: SecretStr

    @model_validator(mode="before")
    @classmethod
    def wrap_sensitive_inputs(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        safe_value = value.copy()
        for field_name in ("card_number", "cvv"):
            sensitive_value = safe_value.get(field_name)
            if not isinstance(sensitive_value, SecretStr):
                safe_value[field_name] = SecretStr(
                    sensitive_value if isinstance(sensitive_value, str) else ""
                )
        return safe_value

    @model_validator(mode="after")
    def validate_card_details(self) -> "PaymentCreate":
        number = self.card_number.get_secret_value()
        cvv = self.cvv.get_secret_value()

        if not (12 <= len(number) <= 19 and number.isascii() and number.isdigit()):
            raise ValueError("Card number must contain 12 to 19 digits")
        if not _passes_luhn(number):
            raise ValueError("Card number is invalid")
        if not (1 <= self.expiry_month <= 12):
            raise ValueError("Expiry month must be between 1 and 12")
        now = datetime.now(UTC)
        if (self.expiry_year, self.expiry_month) < (now.year, now.month):
            raise ValueError("Card has expired")
        if not (cvv.isascii() and cvv.isdigit() and len(cvv) in (3, 4)):
            raise ValueError("CVV must contain 3 or 4 digits")
        return self


def _passes_luhn(number: str) -> bool:
    digits = [int(digit) for digit in number]
    checksum = sum(
        digit * 2 - 9
        if should_double and digit > 4
        else digit * 2
        if should_double
        else digit
        for index, digit in enumerate(reversed(digits))
        for should_double in [index % 2 == 1]
    )
    return checksum % 10 == 0


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    status: str
    amount: Decimal
    provider_reference: str
    card_brand: str
    card_last4: str
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    items: list[OrderItemResponse]


class OrderHistoryResponse(BaseModel):
    orders: list[OrderResponse]
    total_orders: int
    page: int
    page_size: int
