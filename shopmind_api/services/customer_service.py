from shopmind_api.models.customer import Customer
from shopmind_api.repositories.customer_repository import CustomerRepository


class CustomerEmailConflictError(Exception):
    pass


class CustomerService:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def get_customer(self, customer_id: int) -> Customer | None:
        return self.repository.get_by_id(customer_id)
