import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with (
        streamable_http_client("http://127.0.0.1:8001/mcp") as (read, write),
        ClientSession(read, write, read_timeout_seconds=15) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        print("Available tools:", [tool.name for tool in tools.tools])
        result = await session.call_tool(
            "search_products", {"query": "Apple", "limit": 5}
        )
        print(result.model_dump_json(indent=2))
        if result.is_error:
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
