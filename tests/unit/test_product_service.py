from unittest.mock import MagicMock

from shopmind_api.repositories.product_repository import ProductRepository
from shopmind_api.services.product_service import ProductService


def test_get_product_returns_product():
    # Arrange
    mock_repository = MagicMock(spec=ProductRepository)
    expected_product = object()

    mock_repository.get_by_id.return_value = expected_product

    service = ProductService(mock_repository)

    # Act
    result = service.get_product(1)

    # Assert
    assert result is expected_product
    mock_repository.get_by_id.assert_called_once_with(1)


def test_get_product_returns_none_when_not_found():
    mock_repository = MagicMock(spec=ProductRepository)
    mock_repository.get_by_id.return_value = None

    service = ProductService(mock_repository)

    result = service.get_product(999)

    assert result is None
    mock_repository.get_by_id.assert_called_once_with(999)


def test_get_products_returns_page_and_pagination_metadata():
    mock_repository = MagicMock(spec=ProductRepository)
    mock_repository.get_page.return_value = ([], 501)
    service = ProductService(mock_repository)

    result = service.get_products(page=1, page_size=20)

    assert result.products == []
    assert result.pagination.model_dump() == {
        "total_products": 501,
        "current_page": 1,
        "page_size": 20,
    }
    mock_repository.get_page.assert_called_once_with(0, 20)


def test_get_products_returns_zero_total_when_no_products():
    mock_repository = MagicMock(spec=ProductRepository)
    mock_repository.get_page.return_value = ([], 0)
    service = ProductService(mock_repository)

    result = service.get_products(page=1, page_size=20)

    assert result.pagination.model_dump() == {
        "total_products": 0,
        "current_page": 1,
        "page_size": 20,
    }
