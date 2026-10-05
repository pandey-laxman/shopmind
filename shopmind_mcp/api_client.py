from decimal import Decimal
from json import JSONDecodeError

import httpx
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHOPMIND_")

    api_base_url: HttpUrl = HttpUrl("http://127.0.0.1:8000")


class ProductSummary(BaseModel):
    name: str
    description: str | None
    image_url: str | None
    price: Decimal = Field(allow_inf_nan=False)


class ProductSearchResult(BaseModel):
    products: list[ProductSummary] = Field(max_length=20)


class _APIProduct(ProductSummary):
    is_active: bool


class _APIProductSearchResult(BaseModel):
    products: list[_APIProduct]


class CurrentUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    email: str


class InventoryInfo(BaseModel):
    product_id: int
    quantity: int
    is_in_stock: bool


async def search_api_products(
    search: str,
    limit: int,
    min_price: float | str,
    max_price: float | str,
) -> ProductSearchResult:
    try:
        settings = APISettings()
    except ValidationError:
        raise ToolError("ShopMind API URL configuration is invalid.") from None

    try:
        async with httpx.AsyncClient(
            base_url=str(settings.api_base_url),
            timeout=httpx.Timeout(10.0, connect=3.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get(
                "products",
                params={
                    "search": search,
                    "page_size": limit,
                    "page": 1,
                    "min_price": min_price,
                    "max_price": max_price,
                },
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        raise ToolError("ShopMind API request timed out. Try again later.") from None
    except httpx.HTTPStatusError as exc:
        raise ToolError(
            f"ShopMind API returned HTTP {exc.response.status_code}."
        ) from None
    except httpx.RequestError:
        raise ToolError("Unable to reach the ShopMind API. Try again later.") from None

    try:
        api_result = _APIProductSearchResult.model_validate(response.json())
    except (JSONDecodeError, UnicodeDecodeError, ValidationError):
        raise ToolError("ShopMind API returned an invalid product response.") from None

    if len(api_result.products) > limit:
        raise ToolError("ShopMind API returned more products than requested.")
    return ProductSearchResult(
        products=[
            ProductSummary.model_validate(product.model_dump())
            for product in api_result.products
            if product.is_active
        ]
    )


async def get_api_current_user(token: str) -> CurrentUser:
    try:
        settings = APISettings()
    except ValidationError:
        raise ToolError("ShopMind API URL configuration is invalid.") from None

    try:
        async with httpx.AsyncClient(
            base_url=str(settings.api_base_url),
            timeout=httpx.Timeout(10.0, connect=3.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get(
                "auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        raise ToolError("ShopMind API request timed out. Try again later.") from None
    except httpx.HTTPStatusError as exc:
        raise ToolError(
            f"ShopMind API returned HTTP {exc.response.status_code}."
        ) from None
    except httpx.RequestError:
        raise ToolError("Unable to reach the ShopMind API. Try again later.") from None

    try:
        return CurrentUser.model_validate(response.json())
    except (JSONDecodeError, UnicodeDecodeError, ValidationError):
        raise ToolError("ShopMind API returned an invalid customer response.") from None


async def get_api_product_details(product_id: int) -> ProductSummary:
    try:
        settings = APISettings()
    except ValidationError:
        raise ToolError("ShopMind API URL configuration is invalid.") from None

    try:
        async with httpx.AsyncClient(
            base_url=str(settings.api_base_url),
            timeout=httpx.Timeout(10.0, connect=3.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get(f"products/{product_id}")
            response.raise_for_status()
    except httpx.TimeoutException:
        raise ToolError("ShopMind API request timed out. Try again later.") from None
    except httpx.HTTPStatusError as exc:
        raise ToolError(
            f"ShopMind API returned HTTP {exc.response.status_code}."
        ) from None
    except httpx.RequestError:
        raise ToolError("Unable to reach the ShopMind API. Try again later.") from None

    try:
        return ProductSummary.model_validate(response.json())
    except (JSONDecodeError, UnicodeDecodeError, ValidationError):
        raise ToolError("ShopMind API returned an invalid product response.") from None


async def get_api_inventory(product_id: int) -> InventoryInfo:
    try:
        settings = APISettings()
    except ValidationError:
        raise ToolError("ShopMind API URL configuration is invalid.") from None

    try:
        async with httpx.AsyncClient(
            base_url=str(settings.api_base_url),
            timeout=httpx.Timeout(10.0, connect=3.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get(f"inventory/{product_id}")
            response.raise_for_status()
    except httpx.TimeoutException:
        raise ToolError("ShopMind API request timed out. Try again later.") from None
    except httpx.HTTPStatusError as exc:
        raise ToolError(
            f"ShopMind API returned HTTP {exc.response.status_code}."
        ) from None
    except httpx.RequestError:
        raise ToolError("Unable to reach the ShopMind API. Try again later.") from None

    try:
        return InventoryInfo.model_validate(response.json())
    except (JSONDecodeError, UnicodeDecodeError, ValidationError):
        raise ToolError("ShopMind API returned an invalid inventory response.") from None
