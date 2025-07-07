import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
import re
from unicodedata import normalize

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "audio/mpeg",
    "video/mp4",
}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


def generate_object_name(file: UploadFile, user_id: str) -> str:
    ext = Path(file.filename).suffix.lower()
    return f"{file.content_type}/user_{user_id}/{uuid.uuid4().hex}{ext}"


def sanitize_filename(filename: str) -> str:
    cleaned = normalize("NFKD", filename).encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^a-zA-Z0-9\-_.]", "_", cleaned)
    return cleaned[:250]


def validate_file(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Unsupported file type")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            413, f"File size exceeds limit ({MAX_FILE_SIZE//1024//1024})"
        )
