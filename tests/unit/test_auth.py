from datetime import UTC, datetime, timedelta
from decimal import Decimal
import logging

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shopmind_api.core.config import settings
from shopmind_api.core.database import Base
from shopmind_api.core.logging import (
    CorrelationFilter,
    LOG_DIRECTORY,
    SafeFormatter,
    request_id,
)
from shopmind_api.core.security import create_access_token, verify_password
from shopmind_api.dependencies.database import get_db
from shopmind_api.main import app
from shopmind_api.models.customer import Customer
from shopmind_api.models.order import Order
from shopmind_api.schemas.auth import RegisterRequest
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.services.auth_service import AuthService
from shopmind_api.services.customer_service import CustomerEmailConflictError


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Customer(id=1, name="Seeded", email="seeded@example.com"),
                Customer(id=2, name="Admin", email="admin@example.com", role="admin"),
                Customer(id=3, name="Buyer", email="buyer@example.com"),
            ]
        )
        db.flush()
        db.add_all(
            [
                Order(customer_id=1, total_amount=Decimal(1), status="pending"),
                Order(customer_id=3, total_amount=Decimal(2), status="pending"),
            ]
        )
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                yield client, db
        finally:
            app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)
    engine.dispose()


def headers(customer_id):
    return {"Authorization": f"Bearer {create_access_token(customer_id)[0]}"}


def test_registration_login_and_profile(auth_client):
    client, db = auth_client
    payload = {
        "name": "  New Customer  ",
        "email": " NEW@example.com ",
        "password": "  password with spaces  ",
    }
    escalated = client.post("/auth/register", json={**payload, "role": "admin"})
    assert escalated.status_code == 422
    assert payload["password"] not in escalated.text
    registered = client.post("/auth/register", json=payload)
    assert registered.status_code == 201
    assert registered.json()["role"] == "customer"
    assert registered.json()["name"] == "New Customer"
    assert "password_hash" not in registered.text
    customer = db.scalar(select(Customer).where(Customer.email == "new@example.com"))
    assert customer.password_hash.startswith("$argon2id$")
    assert verify_password(payload["password"], customer.password_hash)
    assert not verify_password(payload["password"].strip(), customer.password_hash)
    assert client.post("/auth/register", json=payload).status_code == 409
    logged_in = client.post(
        "/auth/login",
        json={"email": "NEW@example.com", "password": payload["password"]},
    )
    assert logged_in.status_code == 200
    assert (
        logged_in.json()["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    token = logged_in.json()["access_token"]
    correlation_id = "72359052-d6e7-41ba-9958-c12c90aa582d"
    profile = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Request-ID": correlation_id,
        },
    )
    assert profile.json()["id"] == customer.id
    assert profile.headers["X-Request-ID"] == correlation_id
    for filename in ("shopmind.log", "audit.log"):
        output = (LOG_DIRECTORY / filename).read_text()
        assert token not in output
        assert payload["password"] not in output
        assert customer.password_hash not in output
    assert correlation_id in (LOG_DIRECTORY / "shopmind.log").read_text()
    assert client.post("/customers", json=payload).status_code in {404, 405}


def test_seeded_wrong_inactive_and_expired_credentials(auth_client):
    client, db = auth_client
    assert (
        client.post(
            "/auth/login", json={"email": "seeded@example.com", "password": "password"}
        ).status_code
        == 401
    )
    registered = client.post(
        "/auth/register",
        json={
            "name": "Login Buyer",
            "email": "login@example.com",
            "password": "password",
        },
    ).json()
    assert (
        client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "wrongpassword"},
        ).status_code
        == 401
    )
    token = create_access_token(registered["id"])[0]
    db.get(Customer, registered["id"]).is_active = False
    db.commit()
    assert (
        client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "login@example.com", "password": "password"}
        ).status_code
        == 401
    )
    expired = jwt.encode(
        {
            "sub": "1",
            "iat": datetime.now(UTC) - timedelta(minutes=2),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iss": "shopmind",
            "aud": "shopmind-api",
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm="HS256",
    )
    for value in ("malformed", expired):
        assert (
            client.get(
                "/auth/me", headers={"Authorization": f"Bearer {value}"}
            ).status_code
            == 401
        )
    assert client.get("/auth/me").headers["WWW-Authenticate"] == "Bearer"


def test_me_requires_bearer_prefix_and_logs_rejection(auth_client):
    client, _ = auth_client
    token = create_access_token(1)[0]
    correlation_id = "6243e381-1d46-4bbc-87ef-3f829f2c486a"
    response = client.get(
        "/auth/me",
        headers={"Authorization": token, "X-Request-ID": correlation_id},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing access token"}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["X-Request-ID"] == correlation_id
    audit_output = (LOG_DIRECTORY / "audit.log").read_text()
    assert any(
        correlation_id in line and "authentication_failed reason=missing_token" in line
        for line in audit_output.splitlines()
    )
    application_output = (LOG_DIRECTORY / "shopmind.log").read_text()
    assert any(
        correlation_id in line and "route=/auth/me status=401" in line
        for line in application_output.splitlines()
    )
    assert token not in audit_output
    assert token not in application_output
    profile = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["id"] == 1


def test_permissions_ownership_and_database_roles(auth_client):
    client, db = auth_client
    assert client.get("/products").status_code == 200
    assert client.get("/inventory/1").status_code == 404
    assert client.put("/inventory/1", json={"quantity": 1}).status_code == 401
    assert (
        client.put("/inventory/1", json={"quantity": 1}, headers=headers(1)).status_code
        == 403
    )
    assert (
        client.put("/inventory/1", json={"quantity": 1}, headers=headers(2)).status_code
        == 404
    )
    assert client.get("/cart/1").status_code == 401
    assert client.get("/cart/1", headers=headers(1)).status_code == 200
    assert client.get("/cart/3", headers=headers(1)).status_code == 403
    assert client.get("/cart/1", headers=headers(2)).status_code == 403
    assert client.post("/checkout/3", headers=headers(1)).status_code == 403
    assert client.get("/customers/3", headers=headers(1)).status_code == 403
    assert client.get("/customers/3", headers=headers(2)).status_code == 200
    assert client.get("/customers/3/orders", headers=headers(1)).status_code == 403
    assert client.get("/orders/2", headers=headers(1)).status_code == 403
    assert client.get("/orders/2/payments", headers=headers(1)).status_code == 403
    payment = {
        "card_number": "4242424242424242",
        "expiry_month": 12,
        "expiry_year": datetime.now(UTC).year + 1,
        "cvv": "123",
    }
    assert (
        client.post("/orders/2/payments", json=payment, headers=headers(1)).status_code
        == 403
    )
    assert (
        client.post("/orders/2/payments", json=payment, headers=headers(2)).status_code
        == 403
    )
    assert client.get("/orders", headers=headers(1)).json()["total_orders"] == 1
    assert client.get("/orders", headers=headers(2)).json()["total_orders"] == 2
    admin_token = headers(2)
    db.get(Customer, 2).role = "customer"
    db.commit()
    assert (
        client.put(
            "/inventory/1", json={"quantity": 1}, headers=admin_token
        ).status_code
        == 403
    )
    assert client.get("/orders", headers=admin_token).json()["total_orders"] == 0


def test_bootstrap_refuses_existing_accounts(auth_client):
    _, db = auth_client
    service = AuthService(CustomerRepository(db))
    payload = RegisterRequest(
        name="Bootstrap", email="bootstrap@example.com", password="password"
    )
    admin = service.bootstrap_admin(payload)
    assert admin.role == "admin"
    assert verify_password("password", admin.password_hash)
    with pytest.raises(CustomerEmailConflictError):
        service.bootstrap_admin(
            RegisterRequest(
                name="Seeded", email="seeded@example.com", password="password"
            )
        )
    assert db.get(Customer, 1).role == "customer"


def test_safe_exception_logging_and_correlation():
    secret = "password-card-token-sentinel"
    token = request_id.set("correlation-sentinel")
    try:
        try:
            raise RuntimeError(secret)
        except RuntimeError:
            import sys

            record = logging.LogRecord(
                "test", logging.ERROR, __file__, 1, "request_failed", (), sys.exc_info()
            )
        CorrelationFilter().filter(record)
        record.exc_text = f"Cached unsafe exception: {secret}"
        rendered = SafeFormatter("%(request_id)s %(message)s").format(record)
        assert "correlation-sentinel" in rendered
        assert "RuntimeError" in rendered
        assert secret not in rendered
    finally:
        request_id.reset(token)


def test_unexpected_error_is_redacted_and_correlated(auth_client, monkeypatch):
    secret = "exception-password-card-token-sentinel"

    def broken_login(self, payload):
        raise RuntimeError(secret)

    monkeypatch.setattr(AuthService, "login", broken_login)
    correlation_id = "631225e8-9892-4878-b273-3ddfb70ffb03"
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/auth/login",
            json={"email": "buyer@example.com", "password": "password"},
            headers={"X-Request-ID": correlation_id},
        )
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["X-Request-ID"] == correlation_id
    output = (LOG_DIRECTORY / "shopmind.log").read_text()
    assert secret not in output
    assert correlation_id in output
    assert "RuntimeError" in output
