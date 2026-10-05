from fastapi import APIRouter, Depends, HTTPException, status

from shopmind_api.dependencies.auth import get_auth_service, get_current_user
from shopmind_api.models.customer import Customer
from shopmind_api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from shopmind_api.schemas.customer import CustomerResponse
from shopmind_api.services.auth_service import AuthService, InvalidCredentialsError
from shopmind_api.services.customer_service import CustomerEmailConflictError


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=CustomerResponse, status_code=201)
def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> Customer:
    try:
        return service.register(payload)
    except CustomerEmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return service.login(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get("/me", response_model=CustomerResponse)
def me(user: Customer = Depends(get_current_user)) -> Customer:
    return user
