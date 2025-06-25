from fastapi import (
    APIRouter, 
    HTTPException, 
    status, 
    Response, 
    Request, 
    Depends, 
    UploadFile, 
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from minio import Minio

from app.auth.auth import get_password_hash, authenticate_user, create_access_token
from app.dao.user import UserDAO
from app.schemas.user import SUserRegister, SUserAuth
from app.db import User, get_async_db_session, File, UserRole, RefreshToken
from app.dependencies.user import (
    get_current_user, 
    get_current_user_admin,
    get_token
)
from app.auth import (
    get_user_by_refresh_token,
    create_refresh_token,
    save_refresh_token
)
from app.dependencies.minio import get_minio_client
from app.core import settings
from app.helpers.file_utils import (
    generate_object_name,
    sanitize_filename,
    validate_file
)
from app.schemas.file import FileCreateResponse
from app.core.settings import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter(prefix='/auth', tags=['Auth'])


user_roles = [r.value for r in UserRole]


@router.post("/upload", response_model=FileCreateResponse)
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    minio_client: Minio = Depends(get_minio_client),
    db: AsyncSession = Depends(get_async_db_session)
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
            content_type=file.content_type
        )
        
    except Exception as e:
        print(e)
        raise HTTPException(500, "File upload failed")
    
    try:
        async with db.begin():
            db_file = File(
            filename=original_name,
            object_name=object_name,
            content_type=file.content_type,
            size=file_size,
            bucket_name=settings.MINIO_BUCKET,
            owner_id=current_user.id
        )
            db.add(db_file)
            await db.flush()
            await db.refresh(db_file)
            await db.commit()

    except Exception as e:
        await db.rollback()
        
        try:
            minio_client.remove_object(
                settings.MINIO_BUCKET,
                object_name
            )
        except Exception as minio_error:
            print(f"Failed to delete object from MinIO: {str(minio_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

    finally:
        await db.close()
    
    return {
        "id": db_file.id,
        "original_name": db_file.filename,
        "object_name": db_file.object_name,
        "url": f"{settings.MINIO_HOST}:{settings.MINIO_PORT}/{settings.MINIO_BUCKET}/{object_name}",
        "uploaded_at": db_file.uploaded_at
    }


@router.post("/register/")
async def register_user(request: Request, user_data: SUserRegister) -> dict:
    user = await UserDAO.find_one_or_none(email=user_data.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Пользователь уже существует'
        )
    user_dict = user_data.model_dump()
    if user_dict["role"] not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недопустимая роль пользователя!"
        )
    if user_dict["role"] == UserRole.admin:
        token = request.cookies.get("users_access_token")
        if not token:
            is_admin = False
        else:
            user = await get_current_user(token)
            is_admin = await get_current_user_admin(user=user)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав!"
            )
    user_dict['hashed_password'] = get_password_hash(user_data.password)
    user_dict.pop("password")
    await UserDAO.add(**user_dict)
    return {'message': 'Вы успешно зарегистрированы!'}


@router.post("/login/")
async def auth_user(
    request: Request,
    response: Response, 
    user_data: SUserAuth,
    db: AsyncSession = Depends(get_async_db_session)    
):
    user = await authenticate_user(
        email=user_data.email, 
        password=user_data.password
    )
    if user is None :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная почта или пароль"
        )

    old_refresh_token = request.cookies.get("users_refresh_token")
    
    if not old_refresh_token:
        try:
            body = await request.json()
            old_refresh_token = body.get("refresh_token")
        except Exception as e:
            print(f"JSON parse error: {str(e)}")
            old_refresh_token = None
    if old_refresh_token:
        await db.execute(
            delete(RefreshToken).where(RefreshToken.token == old_refresh_token)
        )
        await db.commit()

    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token()

    await save_refresh_token(user.id, refresh_token, db)

    response.set_cookie(
        key="users_access_token", 
        value=access_token, 
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        # secure=True  --- для https в проде 
    )
    
    response.set_cookie(
        key="users_refresh_token", 
        value=refresh_token, 
        httponly=True,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        # path="api/v1/auth/refresh",
        # secure=True  --- для https в проде 
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token    
    }


@router.post("/refresh/")
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db_session)
):
    refresh_token = request.cookies.get("users_refresh_token")

    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception as e:
            print(f"JSON parse error: {str(e)}")
            refresh_token = None

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен не найден"
        )
    
    user = await get_user_by_refresh_token(refresh_token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh токен"
        )
    
    new_access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token()

    await save_refresh_token(user.id, new_refresh_token, db)
    
    await db.execute(
        delete(RefreshToken).where(RefreshToken.token == refresh_token)
    )
    await db.commit()

    response.set_cookie(
        key="users_access_token", 
        value=new_access_token, 
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        # secure=True для прода
    )
    
    response.set_cookie(
        key="users_refresh_token", 
        value=new_refresh_token, 
        httponly=True,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        # path="/auth/refresh",
        # secure=True для прода
    )
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }


@router.get("/me/")
async def get_me(user_data: User = Depends(get_current_user)):
    return user_data


@router.post("/logout/")
async def logout_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db_session),
    user: User = Depends(get_current_user)
):
    refresh_token = request.cookies.get("users_refresh_token")
    if refresh_token:
        await db.execute(
            delete(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        await db.commit()
    
    # Очищаем куки
    response.delete_cookie("users_access_token")
    response.delete_cookie("users_refresh_token")
    
    return {"message": "Успешный выход из системы"}


@router.get("/all_users")
async def get_all_users(user_data: User = Depends(get_current_user_admin)):
    return await UserDAO.find_all()
