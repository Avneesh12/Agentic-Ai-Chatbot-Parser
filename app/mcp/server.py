"""
MCP Server entry point.

Registers all real-world tools and exposes them over the MCP protocol.
Run directly:  python -m app.mcp.server
Or via uvicorn with the FastMCP ASGI adapter.
"""

import logging

from app.mcp.instance import mcp

# ── Import modules so their @mcp.tool() decorators fire ─────────────────────
import app.mcp.tools.health        # noqa: F401  health_check
import app.mcp.tools.real_world    # noqa: F401  get_weather, get_exchange_rate, …

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("mcp-server")


def start():
    logger.info("Starting MCP Server with %d registered tools …", len(mcp._tool_manager._tools))
    mcp.run()


if __name__ == "__main__":
    start()
