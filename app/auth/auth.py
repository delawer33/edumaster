import secrets
from jose import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import RefreshToken
from app.core.settings import get_auth_data
from app.dao.user import UserDAO
from app.core.settings import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_pwd: str, hashed_pwd: str) -> bool:
    return pwd_context.verify(plain_pwd, hashed_pwd)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    auth_data = get_auth_data()
    encode_jwt = jwt.encode(
        to_encode, 
        auth_data["secret_key"], 
        algorithm=auth_data["algorithm"]
    )
    return encode_jwt


def create_refresh_token():
    return secrets.token_urlsafe(64)


async def save_refresh_token(
    user_id: int,
    token: str,
    db: AsyncSession
):
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)

    return db_token


async def get_user_by_refresh_token(
    token: str, 
    db: AsyncSession
):
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.token == token,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
        .options(selectinload(RefreshToken.user))
    )
    token_record = result.scalar_one_or_none()
    return token_record.user if token_record else None


async def authenticate_user(email: EmailStr, password: str):
    user = await UserDAO.find_one_or_none(email=email)
    if not user or verify_password(password, user.hashed_password) is False:
        return None
    return user
