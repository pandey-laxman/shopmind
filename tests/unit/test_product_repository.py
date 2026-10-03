from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shopmind_api.core.database import Base
from shopmind_api.models.category import Category
from shopmind_api.models.product import Product
from shopmind_api.repositories.product_repository import ProductRepository


@pytest.fixture
def product_repository():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        smartphones = Category(name="Smartphones", slug="smartphones")
        laptops = Category(name="Laptops", slug="laptops")
        db.add_all([smartphones, laptops])
        db.flush()
        db.add_all(
            [
                Product(
                    sku="PHONE-1",
                    name="Samsung Phone",
                    description="Flagship smartphone",
                    price=Decimal(700),
                    category=smartphones,
                ),
                Product(
                    sku="PHONE-2",
                    name="Budget Phone",
                    description="Affordable smartphone",
                    price=Decimal(200),
                    category=smartphones,
                ),
                Product(
                    sku="PHONE-3",
                    name="Basic Phone",
                    description="Entry smartphone",
                    price=Decimal(200),
                    category=smartphones,
                ),
                Product(
                    sku="LAPTOP-1",
                    name="Samsung Laptop",
                    description="Work laptop",
                    price=Decimal(900),
                    category=laptops,
                ),
            ]
        )
        db.commit()
        yield ProductRepository(db)

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_get_page_combines_filters_and_counts_only_matching_products(
    product_repository: ProductRepository,
):
    products, total_products = product_repository.get_page(
        offset=1,
        limit=1,
        category="smartphones",
        min_price=Decimal(200),
        max_price=Decimal(700),
        search="phone",
    )

    assert [product.sku for product in products] == ["PHONE-2"]
    assert total_products == 3


@pytest.mark.parametrize("search_term", ["work", "laptop-1"])
def test_get_page_accepts_category_name_and_searches_sku_and_description(
    product_repository: ProductRepository,
    search_term: str,
):
    products, total_products = product_repository.get_page(
        offset=0,
        limit=20,
        category="Laptops",
        search=search_term,
    )

    assert [product.sku for product in products] == ["LAPTOP-1"]
    assert total_products == 1


def test_get_page_uses_product_id_as_stable_sort_tiebreaker(
    product_repository: ProductRepository,
):
    products, total_products = product_repository.get_page(
        offset=0,
        limit=20,
        sort_by="price",
        sort_order="desc",
    )

    assert [product.sku for product in products] == [
        "LAPTOP-1",
        "PHONE-1",
        "PHONE-2",
        "PHONE-3",
    ]
    assert total_products == 4
