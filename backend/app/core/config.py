from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JUDGE_IMAGE: str = "judge-box"
    JUDGE_TIMEOUT_SECONDS: int = 2
    JUDGE_MEMORY_LIMIT: str = "256m"
    JUDGE_CPU_LIMIT: str = "0.5"
    JUDGE_PIDS_LIMIT: int = 64

    YANDEX_API_KEY: str | None = None
    YANDEX_FOLDER_ID: str | None = None
    YANDEX_MAIN_MODEL: str = "aliceai-llm/latest"
    YANDEX_FALLBACK_MODEL: str = "deepseek-v32/latest"
    YANDEX_BASE_URL: str = "https://ai.api.cloud.yandex.net/v1"

    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 1000
    LLM_REQUEST_TIMEOUT_SECONDS: int = 60
    LLM_RETRY_DELAY_SECONDS: int = 90
    LLM_MAX_RETRIES: int = 1
    LLM_DEBUG_LOGGING: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ALEMBIC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg")


settings = Settings()  # type: ignore
