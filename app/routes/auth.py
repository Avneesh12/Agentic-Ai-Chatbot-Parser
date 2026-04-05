from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.db.deps import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, GoogleAuthRequest
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.deps import get_current_user  # 🔹 add this

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": user.avatar,
    }


# ── REGISTER ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_dict(user))


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_dict(user))


# ── GOOGLE OAUTH ──────────────────────────────────────────────────────────────
@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):

    # Verify Google token
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={body.token}"
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_data = response.json()

    # Validate audience
    if google_data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token audience mismatch")

    google_id = google_data.get("sub")
    email     = google_data.get("email")
    name      = google_data.get("name")
    avatar    = google_data.get("picture")

    # Check if user exists by google_id or email
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # Check by email (user may have registered with password before)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Link Google to existing account
            user.google_id = google_id
            user.avatar = avatar
        else:
            # Create new user
            user = User(
                name=name,
                email=email,
                google_id=google_id,
                avatar=avatar,
            )
            db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_dict(user))


# ── LOGOUT ────────────────────────────────────────────────────────────────────
@router.post("/logout")
async def logout():
    # JWT is stateless — logout is handled on frontend by deleting the token
    # For server-side invalidation, use a Redis blacklist
    return {"message": "Logged out successfully"}


# ── ME (get current user) ─────────────────────────────────────────────────────
@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return user_to_dict(current_user)