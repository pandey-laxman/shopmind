from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shopmind_api.schemas.product import ProductResponse


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0, le=2147483647, strict=True)


class CartItemCreate(CartItemUpdate):
    product_id: int = Field(gt=0, le=2147483647, strict=True)


class CartItemResponse(BaseModel):
    product: ProductResponse
    quantity: int
    subtotal: Decimal


class CartResponse(BaseModel):
    customer_id: int
    items: list[CartItemResponse]
    total: Decimal
