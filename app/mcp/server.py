from mcp.server.fastmcp import FastMCP
import logging

# Import tools (IMPORTANT)
from app.mcp.tools import  health
from app.mcp.tools import external_api

# logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")






def start():
    logger.info("🚀 Starting MCP Server...")
    mcp.run()


if __name__ == "__main__":
    start()