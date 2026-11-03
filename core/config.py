from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "root"
    MINIO_SECRET_KEY: str = "rootpassword"
    MINIO_BUCKET: str = "cargo-media"
    MINIO_SECURE: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def MINIO_PUBLIC_BASE(self) -> str:
        scheme = "https" if self.MINIO_SECURE else "http"
        return f"{scheme}://{self.MINIO_ENDPOINT}/{self.MINIO_BUCKET}"

    class Config:
        env_file = ".env"


settings = Settings()
