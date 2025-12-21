from src.server import mcp


def main():
    # Run the MCP server
    # FastMCP uses 'run' to start the server (usually stdio by default for tools)
    mcp.run()


if __name__ == "__main__":
    main()
