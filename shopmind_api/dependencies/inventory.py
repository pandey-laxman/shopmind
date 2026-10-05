from fastapi import Depends
from sqlalchemy.orm import Session

from shopmind_api.dependencies.database import get_db
from shopmind_api.repositories.inventory_repository import InventoryRepository
from shopmind_api.services.inventory_service import InventoryService


def get_inventory_repository(db: Session = Depends(get_db)) -> InventoryRepository:
    return InventoryRepository(db)


def get_inventory_service(
    repository: InventoryRepository = Depends(get_inventory_repository),
) -> InventoryService:
    return InventoryService(repository)
