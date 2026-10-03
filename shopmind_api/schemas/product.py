from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    is_active: bool
    created_at: datetime
    image_url: str | None


class ProductPagination(BaseModel):
    total_products: int
    current_page: int
    page_size: int


class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    pagination: ProductPagination
