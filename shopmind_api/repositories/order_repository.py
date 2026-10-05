from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from shopmind_api.models.cart_item import CartItem
from shopmind_api.models.customer import Customer
from shopmind_api.models.inventory import Inventory
from shopmind_api.models.order import Order
from shopmind_api.models.payment import Payment
from shopmind_api.models.product import Product


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_customer(self, customer_id: int, *, lock: bool = False) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.scalar(stmt)

    def get_cart_items(self, customer_id: int) -> list[CartItem]:
        stmt = (
            select(CartItem)
            .where(CartItem.customer_id == customer_id)
            .order_by(CartItem.product_id)
        )
        return list(self.db.scalars(stmt).all())

    def get_product_for_update(self, product_id: int) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(stmt)

    def get_inventory_for_update(self, product_id: int) -> Inventory | None:
        stmt = (
            select(Inventory)
            .where(Inventory.product_id == product_id)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def create_order(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_order(self, order_id: int, *, lock: bool = False) -> Order | None:
        stmt = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.scalar(stmt)

    def get_order_page(
        self, customer_id: int | None, offset: int, limit: int
    ) -> tuple[list[Order], int]:
        orders_stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(Order)
        if customer_id is not None:
            orders_stmt = orders_stmt.where(Order.customer_id == customer_id)
            count_stmt = count_stmt.where(Order.customer_id == customer_id)
        return (
            list(self.db.scalars(orders_stmt).all()),
            self.db.execute(count_stmt).scalar_one(),
        )

    def get_payments(self, order_id: int) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at, Payment.id)
        )
        return list(self.db.scalars(stmt).all())

    def delete_cart_items(self, customer_id: int) -> None:
        self.db.execute(delete(CartItem).where(CartItem.customer_id == customer_id))

    def add_payment_and_commit(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        self.db.commit()
        self.db.refresh(payment)
        return payment
