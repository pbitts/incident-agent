from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ===============================
    # Model
    # ===============================
    GROQ_API_KEY: str = ""
    MODEL_NAME: str = "openai/gpt-oss-120b"
    MODEL_TEMPERATURE: float = 0.1
    MODEL_MAX_TOKENS: int | None = None

    # ===============================
    # MCP
    # ===============================
    MCP_BASE_URL: str

    # ===============================
    # Timeouts
    # ===============================
    AGENT_TIMEOUT: int = 30
    SUMMARY_TIMEOUT: int = 20

    # ===============================
    # LangSmith
    # ===============================
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: Optional[str] = None

    MONGODB_CHECKPOINTER: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
