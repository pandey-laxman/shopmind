from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status

from shopmind_api.dependencies.cart import get_cart_service
from shopmind_api.dependencies.auth import require_own_customer
from shopmind_api.models.customer import Customer
from shopmind_api.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse
from shopmind_api.services.cart_service import (
    CartConflictError,
    CartNotFoundError,
    CartService,
)


router = APIRouter(prefix="/cart", tags=["Cart"])


def _cart_response(operation: Callable[[], CartResponse]) -> CartResponse:
    try:
        return operation()
    except CartNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CartConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get("/{customer_id}", response_model=CartResponse)
def get_cart(
    customer_id: int,
    user: Customer = Depends(require_own_customer),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return _cart_response(lambda: service.get_cart(user.id))


@router.post("/{customer_id}/items", response_model=CartResponse)
def add_item(
    customer_id: int,
    payload: CartItemCreate,
    user: Customer = Depends(require_own_customer),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return _cart_response(
        lambda: service.add_item(user.id, payload.product_id, payload.quantity)
    )


@router.put("/{customer_id}/items/{product_id}", response_model=CartResponse)
def update_item(
    customer_id: int,
    product_id: int,
    payload: CartItemUpdate,
    user: Customer = Depends(require_own_customer),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return _cart_response(
        lambda: service.update_item(user.id, product_id, payload.quantity)
    )


@router.delete("/{customer_id}/items/{product_id}", response_model=CartResponse)
def remove_item(
    customer_id: int,
    product_id: int,
    user: Customer = Depends(require_own_customer),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return _cart_response(lambda: service.remove_item(user.id, product_id))
