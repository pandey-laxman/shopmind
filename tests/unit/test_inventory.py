from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shopmind_api.core.database import Base
from shopmind_api.core.security import create_access_token
from shopmind_api.dependencies.database import get_db
from shopmind_api.main import app
from shopmind_api.models.inventory import Inventory
from shopmind_api.models.customer import Customer
from shopmind_api.models.product import Product
from shopmind_api.repositories.inventory_repository import InventoryRepository
from shopmind_api.services.inventory_service import InventoryService


@pytest.fixture
def inventory_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(Product(id=1, sku="STOCK-1", name="Stock item", price=Decimal(10)))
        db.commit()
        yield db

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def inventory_client(inventory_db):
    inventory_db.add(
        Customer(id=10, name="Stock Admin", email="admin@example.com", role="admin")
    )
    inventory_db.commit()
    app.dependency_overrides[get_db] = lambda: inventory_db
    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {create_access_token(10)[0]}"
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_inventory_create_update_and_get(inventory_client, inventory_db):
    for quantity in [5, 5, 0, 2147483647]:
        expected = {
            "product_id": 1,
            "quantity": quantity,
            "is_in_stock": quantity > 0,
        }
        response = inventory_client.put("/inventory/1", json={"quantity": quantity})
        assert response.status_code == 200
        assert response.json() == expected

        response = inventory_client.get("/inventory/1")
        assert response.status_code == 200
        assert response.json() == expected
        assert inventory_db.scalar(select(func.count()).select_from(Inventory)) == 1

    inventory_db.expire_all()
    assert inventory_db.get(Inventory, 1).quantity == 2147483647


@pytest.mark.parametrize("product_id", [1, 999])
def test_get_missing_inventory_returns_404(inventory_client, product_id):
    response = inventory_client.get(f"/inventory/{product_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Inventory not found"}


def test_put_unknown_product_returns_404(inventory_client, inventory_db):
    response = inventory_client.put("/inventory/999", json={"quantity": 5})
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
    assert inventory_db.scalar(select(func.count()).select_from(Inventory)) == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"quantity": -1},
        {"quantity": 1.5},
        {"quantity": 1.0},
        {"quantity": True},
        {"quantity": "5"},
        {"quantity": None},
        {"quantity": 2147483648},
        {"quantity": 5, "is_in_stock": False},
    ],
)
def test_put_invalid_quantity_returns_422_without_changing_stock(
    inventory_client, payload
):
    inventory_client.put("/inventory/1", json={"quantity": 3})
    response = inventory_client.put("/inventory/1", json=payload)
    assert response.status_code == 422
    assert inventory_client.get("/inventory/1").json()["quantity"] == 3


@pytest.mark.parametrize("method", ["get", "put"])
def test_invalid_product_id_returns_422(inventory_client, method):
    kwargs = {"json": {"quantity": 5}} if method == "put" else {}
    response = inventory_client.request(method, "/inventory/not-an-id", **kwargs)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "rows",
    [
        [Inventory(product_id=1, quantity=-1)],
        [Inventory(product_id=999, quantity=1)],
        [Inventory(product_id=1, quantity=1), Inventory(product_id=1, quantity=2)],
    ],
)
def test_inventory_database_constraints(inventory_db, rows):
    inventory_db.add_all(rows)
    with pytest.raises(IntegrityError):
        inventory_db.commit()
    inventory_db.rollback()


def test_repository_returns_none_for_missing_records(inventory_db):
    repository = InventoryRepository(inventory_db)
    assert repository.get_by_product_id(1) is None
    assert repository.set_quantity(999, 5) is None


@pytest.mark.parametrize("quantity", [0, 5])
def test_inventory_availability_is_derived(quantity):
    inventory = Inventory(product_id=1, quantity=quantity)
    assert inventory.is_in_stock is (quantity > 0)
    inventory.quantity = 0 if quantity else 5
    assert inventory.is_in_stock is (inventory.quantity > 0)


@pytest.mark.parametrize("found", [True, False])
def test_service_delegates_to_repository(found):
    repository = MagicMock(spec=InventoryRepository)
    inventory = Inventory(product_id=1, quantity=5) if found else None
    repository.get_by_product_id.return_value = inventory
    repository.set_quantity.return_value = inventory
    service = InventoryService(repository)

    assert service.get_inventory(1) is inventory
    assert service.set_quantity(1, 5) is inventory
    repository.get_by_product_id.assert_called_once_with(1)
    repository.set_quantity.assert_called_once_with(1, 5)
