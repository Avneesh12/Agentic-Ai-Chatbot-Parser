"""
Multi-file upload endpoint.

- Accepts 1–20 files in one request (PDF, DOCX, TXT, CSV, XLSX, MD)
- Saves to user-scoped directory so files are isolated per user
- Ingests each file into Qdrant with rich metadata (user_id, filename, file_type, chunk_index)
- Returns a per-file status report so the client knows exactly what succeeded/failed
"""

import os
import uuid
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user
from app.models.user import User
from app.rag.ingest import ingest_file
from app.db.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_BASE_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".md"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_FILES_PER_REQUEST = 20


def _user_upload_dir(user_id: int) -> Path:
    """Each user gets their own folder so filenames never collide."""
    directory = UPLOAD_BASE_DIR / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def _save_file(upload: UploadFile, directory: Path) -> Path:
    """Stream-write the upload to disk safely, preserving original filename."""
    stem = Path(upload.filename).stem
    suffix = Path(upload.filename).suffix.lower()
    unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    dest = directory / unique_name

    content = await upload.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File '{upload.filename}' exceeds {MAX_FILE_SIZE_MB} MB limit.")

    dest.write_bytes(content)
    return dest


@router.post(
    "/kb/upload",
    summary="Upload one or more documents into the RAG knowledge base",
    response_description="Per-file ingestion report",
)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="1–20 files (PDF, DOCX, TXT, CSV, XLSX, MD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Multi-file RAG ingestion endpoint.**

    Upload up to 20 documents in one request. Each file is:
    1. Validated (type + size)
    2. Saved to a user-scoped directory
    3. Chunked, embedded, and stored in Qdrant with metadata
       (user_id, filename, file_type, chunk_index)

    The agent and RAG pipeline filter by user_id automatically,
    so each user only sees answers grounded in their own documents.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES_PER_REQUEST} per request.",
        )

    user_dir = _user_upload_dir(current_user.id)
    results = []

    for upload in files:
        filename = upload.filename or "unnamed"
        suffix = Path(filename).suffix.lower()

        # ── 1. Validate extension ────────────────────────────────────────
        if suffix not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": filename,
                "status": "rejected",
                "reason": f"Unsupported type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            })
            continue

        # ── 2. Save to disk ──────────────────────────────────────────────
        try:
            saved_path = await _save_file(upload, user_dir)
        except ValueError as e:
            results.append({"filename": filename, "status": "rejected", "reason": str(e)})
            continue
        except Exception as e:
            logger.error("Failed to save '%s': %s", filename, e)
            results.append({"filename": filename, "status": "error", "reason": "Disk write failed."})
            continue

        # ── 3. Ingest into Qdrant ────────────────────────────────────────
        try:
            ingest_result = ingest_file(
                path=str(saved_path),
                user_id=current_user.id,
                original_filename=filename,
            )
            results.append({
                "filename": filename,
                "status": "indexed",
                "chunks_inserted": ingest_result["inserted"],
                "saved_as": saved_path.name,
            })
            logger.info(
                "User %s: indexed '%s' → %d chunks",
                current_user.id, filename, ingest_result["inserted"],
            )
        except Exception as e:
            logger.error("Ingestion failed for '%s': %s", filename, e)
            results.append({
                "filename": filename,
                "status": "error",
                "reason": f"Indexing failed: {str(e)}",
                "saved_as": saved_path.name,
            })

    indexed = sum(1 for r in results if r["status"] == "indexed")
    failed = len(results) - indexed

    return JSONResponse(
        status_code=200 if indexed > 0 else 422,
        content={
            "summary": {
                "total": len(results),
                "indexed": indexed,
                "failed": failed,
            },
            "files": results,
        },
    )
