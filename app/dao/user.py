from .base import BaseDAO

from app.db.user import User


class UserDAO(BaseDAO):
    model = User
