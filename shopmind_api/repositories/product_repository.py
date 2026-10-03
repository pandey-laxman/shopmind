from decimal import Decimal
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from shopmind_api.models.category import Category
from shopmind_api.models.product import Product

ProductSortField = Literal["id", "name", "price", "created_at"]


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        """Get a product by its ID."""
        stmt = select(Product).where(Product.id == product_id)
        return self.db.scalar(stmt)

    def get_page(
        self,
        offset: int,
        limit: int,
        category: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        sort_by: ProductSortField = "id",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> tuple[list[Product], int]:
        """Get a filtered, stably sorted product page and its matching total."""
        conditions = []

        if category is not None:
            normalized_category = category.strip().casefold()
            conditions.append(
                Product.category.has(
                    or_(
                        func.lower(Category.name) == normalized_category,
                        func.lower(Category.slug) == normalized_category,
                    )
                )
            )
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        if max_price is not None:
            conditions.append(Product.price <= max_price)
        if search is not None:
            search_term = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.sku.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )

        sort_column = {
            "id": Product.id,
            "name": Product.name,
            "price": Product.price,
            "created_at": Product.created_at,
        }[sort_by]
        primary_order = sort_column.asc() if sort_order == "asc" else sort_column.desc()

        products_stmt = (
            select(Product)
            .where(*conditions)
            .order_by(primary_order, Product.id.asc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(Product).where(*conditions)

        products = list(self.db.scalars(products_stmt).all())
        total_products = self.db.execute(count_stmt).scalar_one()

        return products, total_products
