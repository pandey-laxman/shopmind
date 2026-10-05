import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from shopmind_api.core.security import decode_customer_id
from shopmind_api.dependencies.customer import get_customer_repository
from shopmind_api.dependencies.orders import get_order_repository
from shopmind_api.models.customer import Customer
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.repositories.order_repository import OrderRepository
from shopmind_api.services.auth_service import AuthService


bearer = HTTPBearer(auto_error=False)
audit = logging.getLogger("shopmind.audit")


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_service(
    repository: CustomerRepository = Depends(get_customer_repository),
) -> AuthService:
    return AuthService(repository)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    repository: CustomerRepository = Depends(get_customer_repository),
) -> Customer:
    if credentials is None:
        audit.warning("authentication_failed reason=missing_token")
        raise unauthorized()
    try:
        customer_id = decode_customer_id(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        audit.warning("authentication_failed reason=invalid_token")
        raise unauthorized() from exc
    customer = repository.get_by_id(customer_id)
    if customer is None or not customer.is_active:
        audit.warning("authentication_failed reason=missing_or_inactive_account")
        raise unauthorized()
    return customer


def deny_access(user: Customer) -> None:
    audit.warning("authorization_denied customer_id=%s", user.id)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden"
    )


def require_customer(user: Customer = Depends(get_current_user)) -> Customer:
    if user.role != "customer":
        deny_access(user)
    return user


def require_admin(user: Customer = Depends(get_current_user)) -> Customer:
    if user.role != "admin":
        deny_access(user)
    return user


def require_own_customer(
    customer_id: int,
    user: Customer = Depends(require_customer),
) -> Customer:
    if user.id != customer_id:
        deny_access(user)
    return user


def require_profile_access(
    customer_id: int,
    user: Customer = Depends(get_current_user),
) -> Customer:
    if user.role != "admin" and user.id != customer_id:
        deny_access(user)
    return user


def _check_order_access(
    order_id: int,
    user: Customer,
    repository: OrderRepository,
) -> Customer:
    order = repository.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role != "admin" and order.customer_id != user.id:
        deny_access(user)
    return user


def require_order_access(
    order_id: int,
    user: Customer = Depends(get_current_user),
    repository: OrderRepository = Depends(get_order_repository),
) -> Customer:
    return _check_order_access(order_id, user, repository)


def require_own_order(
    order_id: int,
    user: Customer = Depends(require_customer),
    repository: OrderRepository = Depends(get_order_repository),
) -> Customer:
    return _check_order_access(order_id, user, repository)
