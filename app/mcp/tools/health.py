from app.mcp.instance import mcp

@mcp.tool()
async def health_check() -> dict:
    return {"status": "ok", "message": "Server is running"}

async def list_tools() -> dict:
    return {
        "available_tools": [
            {"name": "health_check",     "description": "Check if server is running",          "input": {}},
            {"name": "list_tools",       "description": "Show all available tools",             "input": {}},
            {"name": "get_posts",        "description": "Get all posts / mock transactions",    "input": {}},
            {"name": "get_post",         "description": "Get single post by ID",                "input": {"post_id": "number"}},
            {"name": "get_users",        "description": "Get list of users / clients",          "input": {}},
            {"name": "get_products",     "description": "Get all products",                     "input": {"limit": "number (default 10)"}},
            {"name": "search_products",  "description": "Search products by keyword",           "input": {"query": "string"}},
            {"name": "get_carts",        "description": "Get shopping carts / purchase orders", "input": {}},
            {"name": "get_store_products","description": "Get products from FakeStore API",     "input": {}},
            {"name": "get_categories",   "description": "Get all product categories",           "input": {}},
            {"name": "get_random_users", "description": "Get random user profiles",             "input": {"count": "number (default 5)"}},
        ],
        "total": 11
    }