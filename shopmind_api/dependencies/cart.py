from fastapi import Depends
from sqlalchemy.orm import Session

from shopmind_api.dependencies.customer import get_customer_repository
from shopmind_api.dependencies.database import get_db
from shopmind_api.dependencies.inventory import get_inventory_repository
from shopmind_api.repositories.cart_repository import CartRepository
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.repositories.inventory_repository import InventoryRepository
from shopmind_api.services.cart_service import CartService


def get_cart_repository(db: Session = Depends(get_db)) -> CartRepository:
    return CartRepository(db)


def get_cart_service(
    repository: CartRepository = Depends(get_cart_repository),
    customer_repository: CustomerRepository = Depends(get_customer_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
) -> CartService:
    return CartService(repository, customer_repository, inventory_repository)
