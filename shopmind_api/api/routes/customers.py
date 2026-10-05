from fastapi import APIRouter, Depends, HTTPException, status

from shopmind_api.dependencies.customer import get_customer_service
from shopmind_api.dependencies.auth import require_profile_access
from shopmind_api.schemas.customer import CustomerResponse
from shopmind_api.services.customer_service import (
    CustomerService,
)


router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_profile_access)],
)
def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
):
    customer = service.get_customer(customer_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    return customer
