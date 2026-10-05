from shopmind_api.models.inventory import Inventory
from shopmind_api.repositories.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository):
        self.repository = repository

    def get_inventory(self, product_id: int) -> Inventory | None:
        return self.repository.get_by_product_id(product_id)

    def set_quantity(self, product_id: int, quantity: int) -> Inventory | None:
        return self.repository.set_quantity(product_id, quantity)
