from .config import Settings

settings = Settings()


class _NoArg:
    """A sentinel value to indicate that a parameter was not given"""


NO_ARG = _NoArg()

DB_HOST = settings.db_settings.host
DB_PORT = settings.db_settings.port
DB_USER = settings.db_settings.user
DB_PASSWORD = settings.db_settings.password.get_secret_value()
DB_NAME = settings.db_settings.name

SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(SQLALCHEMY_DATABASE_URL)

SQLALCHEMY_ECHO = settings.db_settings.echo == "true"

MINIO_USER = settings.minio_settings.user
MINIO_PASSWORD = settings.minio_settings.password.get_secret_value()
MINIO_ACCESS_KEY = settings.minio_settings.access_key
MINIO_SECRET_KEY = settings.minio_settings.secret_key
MINIO_BUCKET = settings.minio_settings.bucket
MINIO_HOST = settings.minio_settings.host
MINIO_PORT = settings.minio_settings.port


RABBITMQ_HOST = settings.rabbitmq_settings.host
RABBITMQ_PORT = settings.rabbitmq_settings.port
RABBITMQ_USER = settings.rabbitmq_settings.user
RABBITMQ_PASS = settings.rabbitmq_settings.password.get_secret_value()

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 1 * 24 * 60  # 1 день
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 дней


def get_auth_data():
    return {"secret_key": settings.secret_key, "algorithm": settings.algorithm}
