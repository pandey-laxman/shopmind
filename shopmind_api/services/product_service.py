from decimal import Decimal
from typing import Literal

from shopmind_api.models.product import Product
from shopmind_api.repositories.product_repository import ProductRepository
from shopmind_api.schemas.product import ProductListResponse, ProductPagination


class ProductService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def get_product(self, product_id: int) -> Product | None:
        return self.repository.get_by_id(product_id)

    def get_products(
        self,
        page: int,
        page_size: int,
        category: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        sort_by: Literal["id", "name", "price", "created_at"] = "id",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> ProductListResponse:
        offset = (page - 1) * page_size
        products, total_products = self.repository.get_page(
            offset=offset,
            limit=page_size,
            category=category,
            min_price=min_price,
            max_price=max_price,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return ProductListResponse(
            products=products,
            pagination=ProductPagination(
                total_products=total_products,
                current_page=page,
                page_size=page_size,
            ),
        )
