import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class DBSettings(BaseSettings):
    name: str
    user: str
    password: SecretStr
    host: str = "localhost"
    port: int = 5435
    echo: bool = False

    model_config = SettingsConfigDict(
        extra="forbid",
    )

class MinioSettings(BaseSettings):
    user: str
    password: SecretStr
    host: str = "localhost"
    port: int = 9000
    bucket: str
    access_key: str
    secret_key: str

    model_config = SettingsConfigDict(
        extra="forbid",
    )

class Settings(BaseSettings):
    app_name: str = "EduMaster"
    debug: bool = False
    db_settings: DBSettings = Field(default_factory=DBSettings)
    minio_settings: MinioSettings = Field(default_factory=MinioSettings)
    secret_key: str
    algorithm: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="forbid",
        env_nested_delimiter="__"
    )
