from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sobriquets"
    POSTGRES_USER: str = "sobriquets"
    POSTGRES_PASSWORD: str = "sobriquets_dev"

    # Embeddings
    EMBEDDING_PROVIDER: str = "sentence_transformers"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    # Agent LLM
    AGENT_LLM_PROVIDER: str = "anthropic"
    AGENT_LLM_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: str = ""

    # Wiki
    WIKI_PATH: str = "./wiki"
    WIKI_PAGES_PATH: str = "./wiki/pages"
    WIKI_RAW_SOURCES_PATH: str = "./wiki/raw-sources"

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
