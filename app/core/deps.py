from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.deps import get_db
from app.core.security import decode_token
from app.models.user import User
from app.core.cache import cache_get, cache_set, cache_delete, make_key
from app.core.config import settings

bearer_scheme = HTTPBearer()


# In get_current_user (deps.py) — cache user lookup
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")

    # 🔹 Check cache first
    user_key = make_key("user", user_id)
    cached = await cache_get(user_key)
    if cached:
        return User(**cached)

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    # 🔹 Cache user data
    await cache_set(user_key, {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "google_id": user.google_id,
        "hashed_password": user.hashed_password,
    }, settings.CACHE_TTL_USER)

    return user

