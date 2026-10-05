from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shopmind_api.core.database import Base
from shopmind_api.core.security import create_access_token
from shopmind_api.dependencies.database import get_db
from shopmind_api.main import app
from shopmind_api.models.cart_item import CartItem
from shopmind_api.models.customer import Customer
from shopmind_api.models.inventory import Inventory
from shopmind_api.models.order import Order
from shopmind_api.models.payment import Payment
from shopmind_api.models.product import Product


@pytest.fixture
def checkout_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)

    db = Session(engine)
    db.add_all(
        [
            Customer(id=1, name="Test Buyer", email="buyer@example.com"),
            Product(
                id=1,
                sku="TEST-1",
                name="Test Product",
                price=Decimal("12.50"),
                is_active=True,
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            Inventory(product_id=1, quantity=10),
            CartItem(customer_id=1, product_id=1, quantity=2),
        ]
    )
    db.commit()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {create_access_token(1)[0]}"
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _payment_payload(card_number: str) -> dict[str, object]:
    return {
        "card_number": card_number,
        "expiry_month": 12,
        "expiry_year": datetime.now(UTC).year + 1,
        "cvv": "9876",
    }


def test_successful_checkout_and_payment_snapshots_and_clears_cart(checkout_client):
    client, db = checkout_client

    checkout = client.post("/checkout/1")
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["status"] == "pending"
    assert order["total_amount"] == "25.00"
    assert order["items"][0]["product_name"] == "Test Product"
    assert order["items"][0]["sku"] == "TEST-1"
    assert order["items"][0]["unit_price"] == "12.50"
    assert db.get(Inventory, 1).quantity == 10

    payment = client.post(
        f"/orders/{order['id']}/payments",
        json=_payment_payload("4242424242424242"),
    )
    assert payment.status_code == 201
    assert payment.json()["status"] == "succeeded"
    assert payment.json()["card_brand"] == "Visa"
    assert payment.json()["card_last4"] == "4242"
    assert "4242424242424242" not in payment.text
    assert "9876" not in payment.text

    assert db.get(Inventory, 1).quantity == 8
    assert db.scalar(select(CartItem)) is None
    assert db.get(Order, order["id"]).status == "confirmed"

    repeated = client.post(
        f"/orders/{order['id']}/payments",
        json=_payment_payload("4242424242424242"),
    )
    assert repeated.status_code == 409


def test_failed_attempt_retains_cart_and_stock_and_can_be_retried(checkout_client):
    client, db = checkout_client
    checkout = client.post("/checkout/1")
    order_id = checkout.json()["id"]

    failed = client.post(
        f"/orders/{order_id}/payments",
        json=_payment_payload("4000000000000002"),
    )
    assert failed.status_code == 201
    assert failed.json()["status"] == "failed"
    assert db.get(Order, order_id).status == "payment_failed"
    assert db.get(Inventory, 1).quantity == 10
    assert db.scalar(select(CartItem)) is not None

    succeeded = client.post(
        f"/orders/{order_id}/payments",
        json=_payment_payload("4242424242424242"),
    )
    assert succeeded.status_code == 201
    assert succeeded.json()["status"] == "succeeded"
    assert db.scalar(select(Order).where(Order.id == order_id)).status == "confirmed"
    assert (
        len(list(db.scalars(select(Payment).where(Payment.order_id == order_id)))) == 2
    )
    assert db.get(Inventory, 1).quantity == 8
    assert db.scalar(select(CartItem)) is None


def test_invalid_card_request_does_not_echo_card_credentials(checkout_client):
    client, _ = checkout_client
    order_id = client.post("/checkout/1").json()["id"]

    response = client.post(
        f"/orders/{order_id}/payments",
        json=_payment_payload("4242424242424241"),
    )

    assert response.status_code == 422
    assert "4242424242424241" not in response.text
    assert "9876" not in response.text
