from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from shopmind_api.models.cart_item import CartItem
from shopmind_api.models.product import Product


class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_items(self, customer_id: int) -> list[CartItem]:
        stmt = (
            select(CartItem)
            .where(CartItem.customer_id == customer_id)
            .options(joinedload(CartItem.product))
            .order_by(CartItem.product_id)
        )
        return list(self.db.scalars(stmt).all())

    def get_item(self, customer_id: int, product_id: int) -> CartItem | None:
        return self.db.get(CartItem, (customer_id, product_id))

    def get_product_for_update(self, product_id: int) -> Product | None:
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        return self.db.scalar(stmt)

    def set_quantity(self, customer_id: int, product_id: int, quantity: int) -> None:
        item = self.get_item(customer_id, product_id)
        if item is None:
            self.db.add(
                CartItem(
                    customer_id=customer_id, product_id=product_id, quantity=quantity
                )
            )
        else:
            item.quantity = quantity
        self.db.flush()

    def remove_item(self, item: CartItem) -> None:
        self.db.delete(item)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()
