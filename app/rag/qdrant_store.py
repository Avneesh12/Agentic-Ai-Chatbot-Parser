from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

COLLECTION = "documents"

def get_qdrant_client() -> QdrantClient:
    # 👉 Production (Cloud)
    if settings.QDRANT_URL and settings.QDRANT_API_KEY:
        return QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )

    # 👉 Local (Docker / localhost)
    return QdrantClient(
        port=settings.QDRANT_PORT
    )


# use this everywhere
client = get_qdrant_client()

def init_collection():
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if COLLECTION not in names:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )