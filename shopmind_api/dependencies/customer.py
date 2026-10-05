from fastapi import Depends
from sqlalchemy.orm import Session

from shopmind_api.dependencies.database import get_db
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.services.customer_service import CustomerService


def get_customer_repository(db: Session = Depends(get_db)) -> CustomerRepository:
    return CustomerRepository(db)


def get_customer_service(
    repository: CustomerRepository = Depends(get_customer_repository),
) -> CustomerService:
    return CustomerService(repository)
