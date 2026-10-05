from sqlalchemy import select
from sqlalchemy.orm import Session

from shopmind_api.models.inventory import Inventory
from shopmind_api.models.product import Product


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_product_id(self, product_id: int) -> Inventory | None:
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        return self.db.scalar(stmt)

    def set_quantity(self, product_id: int, quantity: int) -> Inventory | None:
        # Lock the product even when its inventory does not exist yet.
        product = self.db.scalar(
            select(Product).where(Product.id == product_id).with_for_update()
        )
        if product is None:
            return None

        inventory = self.get_by_product_id(product_id)
        if inventory is None:
            inventory = Inventory(product_id=product_id, quantity=quantity)
            self.db.add(inventory)
        else:
            inventory.quantity = quantity

        self.db.commit()
        self.db.refresh(inventory)
        return inventory
