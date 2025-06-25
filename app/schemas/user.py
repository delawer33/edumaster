from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class SUserRegister(BaseModel):
    username: str = Field(..., min_length=5, max_length=20, description="Имя пользователя, от 5 до 20 знаков")
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    first_name: str = Field(..., min_length=3, max_length=50, description="Имя, от 3 до 50 символов")
    last_name: str = Field(..., min_length=3, max_length=50, description="Фамилия, от 3 до 50 символов")
    role: str = Field(..., min_length=5, max_length=7, description="Роль: student, teacher, admin")


class SUserAuth(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    
