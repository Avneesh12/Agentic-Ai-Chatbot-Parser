from fastapi import FastAPI
from app.routes.chat import router as chat_router
from app.core.config import settings
from app.routes.upload import router as upload_router
from app.db.init_db import init_db
from app.models import chat
from fastapi.middleware.cors import CORSMiddleware
from app.websocket.chat_ws import router as ws_router
from app.routes.document import router as document_router
import threading
from app.mcp.server import start as start_mcp
from app.routes.auth import router as auth_router
from app.core.cache import get_redis, close_redis

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(ws_router)
app.include_router(document_router)
app.include_router(auth_router)

@app.on_event("startup")
async def on_startup():
    await init_db()
    print("✅ Database tables created")
    await get_redis()
    print("[CACHE] Redis connected")
    def run_mcp():
        threading.Thread(target=start_mcp, daemon=True).start()

@app.on_event("shutdown")
async def shutdown():
    await close_redis()
    print("[CACHE] Redis disconnected")
    

@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} is running 🚀"
    }
    