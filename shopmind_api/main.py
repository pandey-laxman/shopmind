from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from shopmind_api.core.config import settings
from shopmind_api.core.logging import configure_logging, RequestLoggingMiddleware
from shopmind_api.core.security import signing_secret
from shopmind_api.api.routes.auth import router as auth_router
from shopmind_api.dependencies.database import get_db
from shopmind_api.api.routes.products import router as products_router
from shopmind_api.api.routes.inventory import router as inventory_router
from shopmind_api.api.routes.customers import router as customers_router
from shopmind_api.api.routes.cart import router as cart_router
from shopmind_api.api.routes.orders import router as orders_router
from shopmind_api.api.routes.checkout import router as checkout_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    signing_secret()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Commerce backend with AI capabilities",
    version=settings.APP_VERSION,
    debug=False,
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    # The request middleware logs a sanitized traceback before this outer handler.
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"X-Request-ID": request.state.request_id},
    )


def _redact_payment_credentials(value):
    if isinstance(value, dict):
        return {
            key: "**********"
            if key.lower()
            in {
                "password",
                "password_hash",
                "access_token",
                "authorization",
                "card_number",
                "cvv",
            }
            else _redact_payment_credentials(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_payment_credentials(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = jsonable_encoder(exc.errors())
    sensitive_request = request.url.path.startswith("/auth/") or (
        request.url.path.startswith("/orders/")
        and request.url.path.endswith("/payments")
    )
    if sensitive_request:
        for error in errors:
            if "input" in error:
                error["input"] = "**********"
            error.pop("ctx", None)
    return JSONResponse(
        status_code=422,
        content={"detail": _redact_payment_credentials(errors)},
    )


app.include_router(auth_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(customers_router)
app.include_router(cart_router)
app.include_router(checkout_router)
app.include_router(orders_router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
