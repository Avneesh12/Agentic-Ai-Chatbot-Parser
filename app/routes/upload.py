from fastapi import APIRouter, UploadFile, File
import os

from app.rag.ingest import ingest_file

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_path = f"{UPLOAD_DIR}/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    ingest_file(file_path)

    return {"message": f"{file.filename} uploaded & indexed ✅"}