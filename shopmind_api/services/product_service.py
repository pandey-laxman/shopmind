from shopmind_api.models.product import Product
from shopmind_api.repositories.product_repository import ProductRepository
from shopmind_api.schemas.product import ProductListResponse, ProductPagination


class ProductService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def get_product(self, product_id: int) -> Product | None:
        return self.repository.get_by_id(product_id)

    def get_products(self, page: int, page_size: int) -> ProductListResponse:
        offset = (page - 1) * page_size
        products, total_products = self.repository.get_page(offset, page_size)

        return ProductListResponse(
            products=products,
            pagination=ProductPagination(
                total_products=total_products,
                current_page=page,
                page_size=page_size,
            ),
        )
