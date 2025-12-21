from src.server import mcp
import asyncio


async def list_tools():
    # FastMCP stores tools in a list or registry.
    # Current version uses decorators to register.
    # We can inspect the underlying list_tools capability.

    # We can use the server's list_tools method directly if exposed,
    # or iterate over the internal registry.

    print("Verifying registered tools...")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(list_tools())
