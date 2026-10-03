from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shopmind_api.models.product import Product


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        """Get a product by its ID."""
        stmt = select(Product).where(Product.id == product_id)
        return self.db.scalar(stmt)

    def get_page(self, offset: int, limit: int) -> tuple[list[Product], int]:
        """Get a stable page of products and the total product count."""
        products_stmt = select(Product).order_by(Product.id).offset(offset).limit(limit)
        count_stmt = select(func.count()).select_from(Product)

        products = list(self.db.scalars(products_stmt).all())
        total_products = self.db.scalar(count_stmt)

        return products, total_products
