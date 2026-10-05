from fastapi import APIRouter, Depends, HTTPException, status

from shopmind_api.dependencies.orders import get_order_service
from shopmind_api.dependencies.auth import require_own_customer
from shopmind_api.models.customer import Customer
from shopmind_api.schemas.order import OrderResponse
from shopmind_api.services.order_service import (
    OrderConflictError,
    OrderNotFoundError,
    OrderService,
)


router = APIRouter(tags=["Checkout"])


@router.post(
    "/checkout/{customer_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    customer_id: int,
    user: Customer = Depends(require_own_customer),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    try:
        return service.checkout(user.id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except OrderConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
