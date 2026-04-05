from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.services.ocr_service import extract_text_from_file
from app.services.document_parser import parse_document

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_TYPES = {"pdf", "png", "jpg", "jpeg", "webp", "tiff", "bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # 🔹 Validate file type
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    # 🔹 Validate file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB.")

    try:
        # 🔹 Step 1: OCR — extract raw text from file
        ocr_result = await extract_text_from_file(file)

        if not ocr_result["full_text"].strip():
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the file. Make sure it's a readable document."
            )

        # 🔹 Step 2: LLM parse — convert raw text to structured JSON
        parsed = await parse_document(ocr_result["full_text"])

        # 🔹 Return full result
        return {
            "status": "success",
            "filename": ocr_result["filename"],
            "file_type": ocr_result["file_type"],
            "total_pages": ocr_result["total_pages"],
            "document_type": parsed.get("document_type"),
            "confidence": parsed.get("confidence"),
            "extracted_data": parsed.get("data"),
            "raw_text": ocr_result["full_text"],  # keep for saving to Chat.document
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")