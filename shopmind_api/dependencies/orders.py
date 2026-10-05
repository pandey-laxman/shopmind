from fastapi import Depends
from sqlalchemy.orm import Session

from shopmind_api.dependencies.database import get_db
from shopmind_api.repositories.order_repository import OrderRepository
from shopmind_api.services.mock_payment_gateway import MockPaymentGateway
from shopmind_api.services.order_service import OrderService


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


def get_order_service(
    repository: OrderRepository = Depends(get_order_repository),
) -> OrderService:
    return OrderService(repository, MockPaymentGateway())
