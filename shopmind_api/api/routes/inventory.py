import logging

from fastapi import APIRouter, Depends, HTTPException, status

from shopmind_api.dependencies.inventory import get_inventory_service
from shopmind_api.dependencies.auth import require_admin
from shopmind_api.models.customer import Customer
from shopmind_api.schemas.inventory import InventoryResponse, InventoryUpdate
from shopmind_api.services.inventory_service import InventoryService


router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory(
    product_id: int,
    service: InventoryService = Depends(get_inventory_service),
):
    inventory = service.get_inventory(product_id)
    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )
    return inventory


@router.put("/{product_id}", response_model=InventoryResponse)
def set_inventory(
    product_id: int,
    payload: InventoryUpdate,
    user: Customer = Depends(require_admin),
    service: InventoryService = Depends(get_inventory_service),
):
    inventory = service.set_quantity(product_id, payload.quantity)
    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    logging.getLogger("shopmind.audit").info(
        "inventory_updated actor_id=%s product_id=%s quantity=%s",
        user.id,
        product_id,
        inventory.quantity,
    )
    return inventory
