from fastapi import APIRouter, Depends, HTTPException, Query, status

from shopmind_api.dependencies.orders import get_order_service
from shopmind_api.dependencies.auth import (
    get_current_user,
    require_order_access,
    require_own_order,
    require_profile_access,
)
from shopmind_api.models.customer import Customer
from shopmind_api.schemas.order import (
    OrderHistoryResponse,
    OrderResponse,
    PaymentCreate,
    PaymentResponse,
)
from shopmind_api.services.order_service import (
    OrderConflictError,
    OrderNotFoundError,
    OrderService,
)


router = APIRouter(tags=["Orders"])


def _raise_order_error(exc: Exception) -> HTTPException:
    if isinstance(exc, OrderNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/orders", response_model=OrderHistoryResponse)
def get_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: Customer = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderHistoryResponse:
    return service.get_orders(
        None if user.role == "admin" else user.id, page, page_size
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_order_access)],
)
def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    try:
        return service.get_order(order_id)
    except OrderNotFoundError as exc:
        raise _raise_order_error(exc) from exc


@router.get(
    "/customers/{customer_id}/orders",
    response_model=OrderHistoryResponse,
    dependencies=[Depends(require_profile_access)],
)
def get_customer_orders(
    customer_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: OrderService = Depends(get_order_service),
) -> OrderHistoryResponse:
    try:
        return service.get_customer_orders(customer_id, page, page_size)
    except OrderNotFoundError as exc:
        raise _raise_order_error(exc) from exc


@router.post(
    "/orders/{order_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_own_order)],
)
def submit_payment(
    order_id: int,
    payload: PaymentCreate,
    service: OrderService = Depends(get_order_service),
) -> PaymentResponse:
    try:
        return service.submit_payment(order_id, payload)
    except (OrderNotFoundError, OrderConflictError) as exc:
        raise _raise_order_error(exc) from exc


@router.get(
    "/orders/{order_id}/payments",
    response_model=list[PaymentResponse],
    dependencies=[Depends(require_order_access)],
)
def get_payments(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> list[PaymentResponse]:
    try:
        return service.get_payments(order_id)
    except OrderNotFoundError as exc:
        raise _raise_order_error(exc) from exc
