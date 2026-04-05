import io
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from fastapi import UploadFile


async def extract_text_from_file(file: UploadFile) -> dict:
    """
    Accepts PDF or image file, returns extracted raw text + metadata.
    """
    content = await file.read()
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1]

    pages_text = []

    if ext == "pdf":
        # Convert PDF pages to images then OCR each
        images = convert_from_bytes(content, dpi=300)
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang="eng")
            pages_text.append({
                "page": i + 1,
                "text": text.strip()
            })

    elif ext in ("png", "jpg", "jpeg", "webp", "tiff", "bmp"):
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image, lang="eng")
        pages_text.append({
            "page": 1,
            "text": text.strip()
        })

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    full_text = "\n\n".join([p["text"] for p in pages_text])

    return {
        "filename": filename,
        "file_type": ext,
        "total_pages": len(pages_text),
        "pages": pages_text,
        "full_text": full_text,
    }