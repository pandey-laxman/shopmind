from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from shopmind_api.dependencies.product import get_product_service
from shopmind_api.services.product_service import ProductService
from shopmind_api.schemas.product import ProductListResponse, ProductResponse


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
def get_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None, min_length=1),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    search: str | None = Query(default=None, min_length=1),
    sort_by: Literal["id", "name", "price", "created_at"] = "id",
    sort_order: Literal["asc", "desc"] = "asc",
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_price must be less than or equal to max_price",
        )

    return service.get_products(
        page=page,
        page_size=page_size,
        category=category,
        min_price=min_price,
        max_price=max_price,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    product = service.get_product(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product
