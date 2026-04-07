"""
Document ingestion pipeline.

Supports: PDF, DOCX, TXT, CSV, XLSX, MD
Each chunk is stored in Qdrant with rich metadata so the RAG retriever
can filter by user_id, filename, or file_type at query time.

Chunking uses a sliding window with overlap so sentences that span chunk
boundaries are never silently dropped.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import List

from pypdf import PdfReader
from docx import Document
import pandas as pd

from app.rag.embedding import embed_text
from app.rag.qdrant_store import client, COLLECTION, init_collection
from qdrant_client.models import PointStruct

logger = logging.getLogger(__name__)

# ── Chunking config ──────────────────────────────────────────────────────────
CHUNK_SIZE = 512        # characters per chunk
CHUNK_OVERLAP = 64      # characters of overlap between consecutive chunks


# ── File loaders ─────────────────────────────────────────────────────────────

def _load_pdf(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {i+1}]\n{text}")
    return "\n\n".join(pages)


def _load_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _load_txt_md(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _load_csv(path: str) -> str:
    df = pd.read_csv(path)
    # Convert to a readable text table (first 500 rows to stay reasonable)
    sample = df.head(500)
    return f"CSV file with {len(df)} rows and columns: {', '.join(df.columns)}\n\n{sample.to_string(index=False)}"


def _load_xlsx(path: str) -> str:
    xl = pd.ExcelFile(path)
    parts = []
    for sheet in xl.sheet_names:
        df = xl.parse(sheet).head(500)
        parts.append(f"[Sheet: {sheet}]\n{df.to_string(index=False)}")
    return "\n\n".join(parts)


LOADERS = {
    ".pdf":  _load_pdf,
    ".docx": _load_docx,
    ".txt":  _load_txt_md,
    ".md":   _load_txt_md,
    ".csv":  _load_csv,
    ".xlsx": _load_xlsx,
}


def load_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    loader = LOADERS.get(ext)
    if not loader:
        raise ValueError(f"Unsupported file type: '{ext}'")
    return loader(path)


# ── Chunking ─────────────────────────────────────────────────────────────────

def sliding_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping windows.
    This prevents information loss at chunk boundaries.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap          # step forward by (size - overlap)
        if start >= len(text):
            break
    return [c.strip() for c in chunks if c.strip()]


# ── Main entry point ─────────────────────────────────────────────────────────

def ingest_file(path: str, user_id: int, original_filename: str) -> dict:
    """
    Load → chunk → embed → upsert into Qdrant.

    Every Qdrant point carries:
      - text         : the raw chunk text
      - user_id      : owner of the document (used for per-user filtering)
      - filename     : original upload name shown to the user
      - file_type    : extension (pdf, docx …)
      - chunk_index  : position within the document (useful for reranking)
    """
    ext = Path(path).suffix.lower().lstrip(".")
    text = load_file(path)

    if not text.strip():
        raise ValueError("Document appears to be empty — no text could be extracted.")

    chunks = sliding_chunks(text)
    if not chunks:
        raise ValueError("No usable text chunks produced from the document.")

    vectors = embed_text(chunks)
    init_collection()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={
                "text":           chunks[i],
                "user_id":        user_id,
                "filename":       original_filename,
                "file_type":      ext,
                "chunk_index":    i,
                "total_chunks":   len(chunks),
            },
        )
        for i in range(len(chunks))
    ]

    client.upsert(collection_name=COLLECTION, points=points)

    logger.info(
        "Ingested '%s' for user %s: %d chunks from %d chars",
        original_filename, user_id, len(points), len(text),
    )

    return {
        "inserted": len(points),
        "filename": original_filename,
        "file_type": ext,
        "char_count": len(text),
    }
