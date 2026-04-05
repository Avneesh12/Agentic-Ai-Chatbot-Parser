from app.mcp.tools.health import health_check
from app.mcp.tools.external_api import (
    get_posts,
    get_post,
    get_users,
    get_products,
    search_products,
    get_carts,
    get_store_products,
    get_categories,
    get_random_users
)

TOOLS = {
    "health_check": health_check,
    "get_posts": get_posts,
    "get_post": get_post,
    "get_users": get_users,
    "get_products": get_products,
    "search_products": search_products,
    "get_carts": get_carts,
    "get_store_products": get_store_products,
    "get_categories": get_categories,
    "get_random_users": get_random_users
}


