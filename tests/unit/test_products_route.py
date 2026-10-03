from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from shopmind_api.dependencies.product import get_product_service
from shopmind_api.main import app
from shopmind_api.schemas.product import ProductListResponse, ProductPagination
from shopmind_api.services.product_service import ProductService


@pytest.fixture
def client():
    service = MagicMock(spec=ProductService)

    def get_products(**kwargs):
        return ProductListResponse(
            products=[],
            pagination=ProductPagination(
                total_products=0,
                current_page=kwargs["page"],
                page_size=kwargs["page_size"],
            ),
        )

    service.get_products.side_effect = get_products
    app.dependency_overrides[get_product_service] = lambda: service

    with TestClient(app) as test_client:
        yield test_client, service

    app.dependency_overrides.clear()


def test_get_products_passes_combined_filters_and_sorting(client):
    test_client, service = client

    response = test_client.get(
        "/products",
        params={
            "category": "laptops",
            "max_price": "80000",
            "search": "samsung",
            "page": "1",
            "page_size": "10",
            "sort_by": "price",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "total_products": 0,
        "current_page": 1,
        "page_size": 10,
    }
    service.get_products.assert_called_once()
    arguments = service.get_products.call_args.kwargs
    assert arguments["category"] == "laptops"
    assert str(arguments["max_price"]) == "80000"
    assert arguments["search"] == "samsung"
    assert arguments["page"] == 1
    assert arguments["page_size"] == 10
    assert arguments["sort_by"] == "price"
    assert arguments["sort_order"] == "asc"


@pytest.mark.parametrize(
    "params",
    [
        {"min_price": "800", "max_price": "200"},
        {"page": "0"},
        {"page_size": "101"},
        {"sort_by": "sku"},
        {"sort_order": "sideways"},
    ],
)
def test_get_products_rejects_invalid_parameters(client, params):
    test_client, service = client

    response = test_client.get("/products", params=params)

    assert response.status_code == 422
    service.get_products.assert_not_called()
