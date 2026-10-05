import asyncio
import runpy
from pathlib import Path
from unittest.mock import patch

from mcp import Client
from mcp.server import MCPServer

from shopmind_mcp.server import mcp


def test_server_discovers_search_products():
    async def check():
        async with Client(mcp) as client:
            result = await client.list_tools()
            assert [tool.name for tool in result.tools] == [
                "search_products",
                "get_current_user",
            ]
            tool = result.tools[0]
            assert tool.description == (
                "Search ShopMind products and return names, descriptions, image URLs, and prices."
            )
            schema = tool.input_schema
            assert schema["required"] == ["query"]
            assert schema["properties"]["query"]["type"] == "string"
            assert schema["properties"]["query"]["maxLength"] == 200
            assert schema["properties"]["query"]["pattern"] == r"\S"
            assert schema["properties"]["limit"]["type"] == "integer"
            assert schema["properties"]["limit"]["default"] == 10
            assert schema["properties"]["limit"]["minimum"] == 1
            assert schema["properties"]["limit"]["maximum"] == 20
            product_schema = tool.output_schema["$defs"]["ProductSummary"]
            assert set(product_schema["properties"]) == {
                "name",
                "description",
                "image_url",
                "price",
            }

    assert isinstance(mcp, MCPServer)
    assert mcp.name == "ShopMind"
    asyncio.run(check())


def test_entry_point_runs_streamable_http():
    entry_point = Path(__file__).resolve().parents[1] / "shopmind_mcp" / "server.py"
    with patch.object(MCPServer, "run") as run:
        runpy.run_path(str(entry_point), run_name="__main__")

    run.assert_called_once_with(transport="streamable-http", port=8001)
