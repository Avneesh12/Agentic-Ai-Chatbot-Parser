from pypdf import PdfReader
from docx import Document
from qdrant_client.models import PointStruct
import uuid, os

from app.rag.embedding import embed_text
from app.rag.qdrant_store import client, COLLECTION, init_collection


def load_file(path):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(path)
        return "".join([p.extract_text() or "" for p in reader.pages])

    elif ext == ".txt":
        return open(path, encoding="utf-8").read()

    elif ext == ".docx":
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        raise Exception("Unsupported file")


def chunk(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]


def ingest_file(path):
    text = load_file(path)

    if not text.strip():
        raise Exception("Empty file")

    chunks = chunk(text)

    vectors = embed_text(chunks)

    init_collection()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={"text": chunks[i]}
        )
        for i in range(len(chunks))
    ]

    client.upsert(collection_name=COLLECTION, points=points)

    return {"inserted": len(points)}