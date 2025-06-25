from jose import jwt, JWTError
from fastapi import Request, status, HTTPException, Depends
from datetime import datetime, timezone

from app.core.settings import get_auth_data
from app.dao.user import UserDAO
from app.db import User
from app.db.user import UserRole


def get_token(request: Request):
    token = request.cookies.get("users_access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден"
        )
    return token


async def get_current_user(token: str = Depends(get_token)):
    try:
        auth_data = get_auth_data()
        payload = jwt.decode(
            token, 
            auth_data["secret_key"], 
            algorithms=[auth_data["algorithm"]]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не валидный"
        )
    
    expire = payload.get("exp")
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if (not expire) or (expire_time < datetime.now(timezone.utc)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен Истек"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не найден ID пользователя"
        )
    
    user = await UserDAO.find_one_or_none_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь с таким ID не найден"
        )
    
    return user


async def get_current_user_admin(user: User = Depends(get_current_user)):
    if user.role == UserRole.admin:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав"
    )


async def get_current_user_teacher(user: User = Depends(get_current_user)):
    if user.role == UserRole.teacher or user.role == UserRole.admin:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав"
    )

