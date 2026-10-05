from decimal import Decimal
import logging

from shopmind_api.models.inventory import Inventory
from shopmind_api.models.order import Order
from shopmind_api.models.order_item import OrderItem
from shopmind_api.models.payment import Payment
from shopmind_api.repositories.order_repository import OrderRepository
from shopmind_api.schemas.order import (
    OrderHistoryResponse,
    OrderResponse,
    PaymentCreate,
    PaymentResponse,
)
from shopmind_api.services.mock_payment_gateway import MockPaymentGateway


class OrderNotFoundError(Exception):
    pass


class OrderConflictError(Exception):
    pass


class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        payment_gateway: MockPaymentGateway,
    ):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, customer_id: int) -> OrderResponse:
        if self.repository.get_customer(customer_id, lock=True) is None:
            raise OrderNotFoundError("Customer not found")

        cart_items = self.repository.get_cart_items(customer_id)
        if not cart_items:
            raise OrderConflictError("Cannot checkout an empty cart")

        order_items: list[OrderItem] = []
        total_amount = Decimal("0.00")
        for cart_item in cart_items:
            product = self.repository.get_product_for_update(cart_item.product_id)
            if product is None:
                raise OrderNotFoundError("Product not found")
            if not product.is_active:
                raise OrderConflictError(f"Product {product.sku} is inactive")

            inventory = self.repository.get_inventory_for_update(product.id)
            if inventory is None or cart_item.quantity > inventory.quantity:
                raise OrderConflictError(
                    f"Insufficient inventory for product {product.sku}"
                )

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    unit_price=product.price,
                    quantity=cart_item.quantity,
                )
            )
            total_amount += product.price * cart_item.quantity

        order = Order(
            customer_id=customer_id,
            status="pending",
            total_amount=total_amount,
            items=order_items,
        )
        result = OrderResponse.model_validate(self.repository.create_order(order))
        logging.getLogger("shopmind.audit").info(
            "order_created customer_id=%s order_id=%s", customer_id, result.id
        )
        return result

    def get_order(self, order_id: int) -> OrderResponse:
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError("Order not found")
        return OrderResponse.model_validate(order)

    def get_customer_orders(
        self, customer_id: int, page: int, page_size: int
    ) -> OrderHistoryResponse:
        if self.repository.get_customer(customer_id) is None:
            raise OrderNotFoundError("Customer not found")
        return self.get_orders(customer_id, page, page_size)

    def get_orders(
        self, customer_id: int | None, page: int, page_size: int
    ) -> OrderHistoryResponse:
        orders, total_orders = self.repository.get_order_page(
            customer_id, (page - 1) * page_size, page_size
        )
        return OrderHistoryResponse(
            orders=[OrderResponse.model_validate(order) for order in orders],
            total_orders=total_orders,
            page=page,
            page_size=page_size,
        )

    def get_payments(self, order_id: int) -> list[PaymentResponse]:
        if self.repository.get_order(order_id) is None:
            raise OrderNotFoundError("Order not found")
        return [
            PaymentResponse.model_validate(payment)
            for payment in self.repository.get_payments(order_id)
        ]

    def submit_payment(self, order_id: int, payload: PaymentCreate) -> PaymentResponse:
        order = self.repository.get_order(order_id, lock=True)
        if order is None:
            raise OrderNotFoundError("Order not found")
        if order.status == "confirmed":
            raise OrderConflictError("Order has already been confirmed")

        gateway_result = self.payment_gateway.authorize(
            payload.card_number.get_secret_value(),
            payload.expiry_month,
            payload.expiry_year,
            payload.cvv.get_secret_value(),
        )

        succeeded = gateway_result.succeeded
        locked_inventory: list[Inventory] = []
        if succeeded:
            self.repository.get_customer(order.customer_id, lock=True)
            available_inventory = self._lock_available_stock(order)
            if available_inventory is None:
                succeeded = False
            else:
                locked_inventory = available_inventory

        if succeeded:
            for item, inventory in zip(
                sorted(order.items, key=lambda order_item: order_item.product_id),
                locked_inventory,
                strict=True,
            ):
                inventory.quantity -= item.quantity

        if succeeded:
            order.status = "confirmed"
            self.repository.delete_cart_items(order.customer_id)
        else:
            order.status = "payment_failed"

        payment = Payment(
            order_id=order.id,
            status="succeeded" if succeeded else "failed",
            amount=order.total_amount,
            provider_reference=gateway_result.provider_reference,
            card_brand=gateway_result.card_brand,
            card_last4=gateway_result.card_last4,
        )
        result = PaymentResponse.model_validate(
            self.repository.add_payment_and_commit(payment)
        )
        logging.getLogger("shopmind.audit").info(
            "payment_outcome customer_id=%s order_id=%s payment_id=%s status=%s",
            order.customer_id,
            order.id,
            result.id,
            result.status,
        )
        return result

    def _lock_available_stock(self, order: Order) -> list[Inventory] | None:
        inventories: list[Inventory] = []
        for item in sorted(order.items, key=lambda order_item: order_item.product_id):
            product = self.repository.get_product_for_update(item.product_id)
            inventory = self.repository.get_inventory_for_update(item.product_id)
            if (
                product is None
                or not product.is_active
                or inventory is None
                or inventory.quantity < item.quantity
            ):
                return None
            inventories.append(inventory)
        return inventories
