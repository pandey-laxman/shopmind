from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Literal

from shopmind_api.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: int, *, lock: bool = False) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id)
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_by_email(self, email: str) -> Customer | None:
        return self.db.scalar(select(Customer).where(Customer.email == email))

    def create(
        self,
        name: str,
        email: str,
        *,
        password_hash: str,
        role: Literal["customer", "admin"] = "customer",
    ) -> Customer:
        customer = Customer(
            name=name, email=email, password_hash=password_hash, role=role
        )
        self.db.add(customer)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(customer)
        return customer
