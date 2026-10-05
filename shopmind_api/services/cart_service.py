from decimal import Decimal

from shopmind_api.repositories.cart_repository import CartRepository
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.repositories.inventory_repository import InventoryRepository
from shopmind_api.schemas.cart import CartItemResponse, CartResponse
from shopmind_api.schemas.product import ProductResponse


class CartNotFoundError(Exception):
    pass


class CartConflictError(Exception):
    pass


class CartService:
    def __init__(
        self,
        repository: CartRepository,
        customer_repository: CustomerRepository,
        inventory_repository: InventoryRepository,
    ):
        self.repository = repository
        self.customer_repository = customer_repository
        self.inventory_repository = inventory_repository

    def _require_customer(self, customer_id: int, *, lock: bool = False) -> None:
        if self.customer_repository.get_by_id(customer_id, lock=lock) is None:
            raise CartNotFoundError("Customer not found")

    def _build_cart(self, customer_id: int) -> CartResponse:
        items = [
            CartItemResponse(
                product=ProductResponse.model_validate(item.product),
                quantity=item.quantity,
                subtotal=item.product.price * item.quantity,
            )
            for item in self.repository.get_items(customer_id)
        ]
        return CartResponse(
            customer_id=customer_id,
            items=items,
            total=sum((item.subtotal for item in items), Decimal("0.00")),
        )

    def get_cart(self, customer_id: int) -> CartResponse:
        self._require_customer(customer_id)
        return self._build_cart(customer_id)

    def add_item(
        self, customer_id: int, product_id: int, quantity: int
    ) -> CartResponse:
        return self._set_quantity(customer_id, product_id, quantity, increment=True)

    def update_item(
        self, customer_id: int, product_id: int, quantity: int
    ) -> CartResponse:
        return self._set_quantity(customer_id, product_id, quantity, increment=False)

    def _set_quantity(
        self, customer_id: int, product_id: int, quantity: int, *, increment: bool
    ) -> CartResponse:
        # Serialize changes to a customer's cart, including first-time inserts.
        self._require_customer(customer_id, lock=True)
        product = self.repository.get_product_for_update(product_id)
        if product is None:
            raise CartNotFoundError("Product not found")
        if not product.is_active:
            raise CartConflictError("Product is inactive")

        item = self.repository.get_item(customer_id, product_id)
        if not increment and item is None:
            raise CartNotFoundError("Cart item not found")
        if increment and item is not None:
            quantity += item.quantity

        inventory = self.inventory_repository.get_by_product_id(product_id)
        if inventory is None or quantity > inventory.quantity:
            raise CartConflictError("Requested quantity exceeds available inventory")

        self.repository.set_quantity(customer_id, product_id, quantity)
        cart = self._build_cart(customer_id)
        self.repository.commit()
        return cart

    def remove_item(self, customer_id: int, product_id: int) -> CartResponse:
        self._require_customer(customer_id, lock=True)
        item = self.repository.get_item(customer_id, product_id)
        if item is None:
            raise CartNotFoundError("Cart item not found")
        self.repository.remove_item(item)
        cart = self._build_cart(customer_id)
        self.repository.commit()
        return cart
