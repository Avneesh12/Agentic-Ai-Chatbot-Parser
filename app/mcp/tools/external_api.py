import httpx

async def get_random_users(count: int = 5) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://randomuser.me/api/",
            params={"results": count}   # 🔹 pass as params not f-string
        )
        return response.json()

async def get_products(limit: int = 10) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://dummyjson.com/products?limit={limit}")
        return response.json()

async def search_products(query: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://dummyjson.com/products/search?q={query}")
        return response.json()

async def get_posts() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts")
        return response.json()

async def get_post(post_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://jsonplaceholder.typicode.com/posts/{post_id}")
        return response.json()

async def get_users() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://dummyjson.com/users")
        return response.json()

async def get_carts() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://dummyjson.com/carts")
        return response.json()

async def get_store_products() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://fakestoreapi.com/products")
        return response.json()

async def get_categories() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://dummyjson.com/products/categories")
        return response.json()