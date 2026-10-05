from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from shopmind_mcp.api_client import (
    CurrentUser,
    InventoryInfo,
    ProductSearchResult,
    ProductSummary,
    get_api_current_user,
    get_api_inventory,
    get_api_product_details,
    search_api_products,
)

mcp = MCPServer("ShopMind")


@mcp.tool(name="search_products")
async def search_products(
    search: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            pattern=r"\S",
            strict=True,
            description="Text to search for in the ShopMind product catalogue.",
        ),
    ],
    limit: Annotated[
        int, Field(ge=1, le=20, strict=True, description="Maximum number of results.")
    ] = 10,
    min_price: float | str = 0,
    max_price: float | str = 0,
) -> ProductSearchResult:
    """Search ShopMind products and return names, descriptions, image URLs, and prices."""
    return await search_api_products(search, limit, min_price, max_price)


@mcp.tool(name="get_product_details")
async def get_product_details(
    product_id: Annotated[int, Field(strict=True)],
) -> ProductSummary:
    """Get a ShopMind product's name, description, image URL, and price."""
    return await get_api_product_details(product_id)


@mcp.tool(name="check_inventory")
async def check_inventory(
    product_id: Annotated[int, Field(strict=True)],
) -> InventoryInfo:
    """Check the available quantity and in-stock status for a product."""
    return await get_api_inventory(product_id)


@mcp.tool(name="get_current_user")
async def get_current_user(ctx: Context) -> CurrentUser:
    """Get the authenticated customer's ID, name, and email."""
    authorization = (ctx.headers or {}).get("authorization")
    parts = authorization.split() if authorization else []
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise ToolError("A Bearer token is required to get the current user.")
    return await get_api_current_user(parts[1])


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8001)
