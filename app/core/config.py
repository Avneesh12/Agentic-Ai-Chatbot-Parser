import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AI Chat API")
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    MODEL: str = os.getenv("MODEL", "google/gemma-7b-it:free")
    GROQ_API_KEY : str = os.getenv("GROQ_API_KEY")
    QDRANT_HOST = os.getenv("QDRANT_HOST", None)
    QDRANT_PORT = int(os.getenv("QDRANT_PORT",6333))
    QDRANT_URL = os.getenv("QDRANT_URL", None)
    QDRANT_API_KEY = os.getenv("QDRANT_PORT")
    HF_API_KEY = os.getenv("HF_API_KEY")
    
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT")
    DB_NAME: str = os.getenv("DB_NAME")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY","")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    
    REDIS_URL: str = os.getenv("REDIS_URL", None)

    # Cache TTLs (seconds)
    CACHE_TTL_CHAT_HISTORY: int = 60 * 5       # 5 min
    CACHE_TTL_RAG_ANSWER: int   = 60 * 60      # 1 hour
    CACHE_TTL_TOOL_RESULT: int  = 60 * 2       # 2 min
    CACHE_TTL_USER: int         = 60 * 15      # 15 min

    class Config:
        env_file = ".env"

    @property
    def DATABASE_URL(self):
        return (
            f"postgresql+asyncpg://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.DB_NAME}"
        )

settings = Settings()