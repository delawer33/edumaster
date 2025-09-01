from fastapi import (
    HTTPException,
    status,
    Depends,
    APIRouter,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession
from minio import Minio

from app.db import User, get_async_db_session, File
from app.dependencies.user import get_current_user
from app.dependencies.minio import get_minio_client
from app.core import settings
from app.helpers.file_utils import (
    generate_object_name,
    sanitize_filename,
    validate_file,
)
from app.schemas.file import FileCreateResponse

router = APIRouter(prefix="/upload", tags=["Files"])

@router.post("/", response_model=FileCreateResponse)
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    minio_client: Minio = Depends(get_minio_client),
    db: AsyncSession = Depends(get_async_db_session),
):
    validate_file(file)

    object_name = generate_object_name(file, current_user.id)
    original_name = sanitize_filename(file.filename)

    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            file.file,
            length=file_size,
            content_type=file.content_type,
        )

    except Exception as e:
        raise HTTPException(500, "File upload failed")

    try:
        async with db.begin():
            db_file = File(
                filename=original_name,
                object_name=object_name,
                content_type=file.content_type,
                size=file_size,
                bucket_name=settings.MINIO_BUCKET,
                owner_id=current_user.id,
            )
            db.add(db_file)
            await db.flush()
            await db.refresh(db_file)
            await db.commit()

    except Exception as e:
        await db.rollback()

        try:
            minio_client.remove_object(settings.MINIO_BUCKET, object_name)
        except Exception as minio_error:
            print(f"Failed to delete object from MinIO: {str(minio_error)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    return {
        "id": db_file.id,
        "original_name": db_file.filename,
        "object_name": db_file.object_name,
        "uploaded_at": db_file.uploaded_at,
    }
