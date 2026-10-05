import logging
from typing import Literal

from sqlalchemy.exc import IntegrityError

from shopmind_api.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from shopmind_api.models.customer import Customer
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from shopmind_api.services.customer_service import CustomerEmailConflictError


audit = logging.getLogger("shopmind.audit")


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def register(self, payload: RegisterRequest) -> Customer:
        return self._create_account(payload, role="customer")

    def bootstrap_admin(self, payload: RegisterRequest) -> Customer:
        return self._create_account(payload, role="admin")

    def _create_account(
        self, payload: RegisterRequest, *, role: Literal["customer", "admin"]
    ) -> Customer:
        try:
            customer = self.repository.create(
                payload.name,
                str(payload.email),
                password_hash=hash_password(payload.password.get_secret_value()),
                role=role,
            )
        except IntegrityError as exc:
            if self.repository.get_by_email(str(payload.email)) is not None:
                audit.warning("registration_failed reason=email_conflict role=%s", role)
                raise CustomerEmailConflictError(
                    "A customer with this email already exists"
                ) from exc
            raise
        audit.info("account_created customer_id=%s role=%s", customer.id, customer.role)
        return customer

    def login(self, payload: LoginRequest) -> TokenResponse:
        customer = self.repository.get_by_email(str(payload.email))
        valid = verify_password(
            payload.password.get_secret_value(),
            customer.password_hash if customer else None,
        )
        if customer is None or not valid or not customer.is_active:
            audit.warning("login_failed reason=invalid_credentials")
            raise InvalidCredentialsError("Invalid email or password")
        token, expires_in = create_access_token(customer.id)
        audit.info("login_succeeded customer_id=%s", customer.id)
        return TokenResponse(access_token=token, expires_in=expires_in)
