from sqlalchemy.orm import Session
from fastapi import Depends

from shopmind_api.dependencies.database import get_db
from shopmind_api.repositories.product_repository import ProductRepository
from shopmind_api.services.product_service import ProductService


def get_product_repository(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_product_service(
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    return ProductService(repository)
