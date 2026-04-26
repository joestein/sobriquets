import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sobriquets.api.routes import init_routes, router
from sobriquets.agent.tools import set_embedding_provider
from sobriquets.config import get_settings
from sobriquets.db.models import Base
from sobriquets.db.session import get_engine, init_engine
from sobriquets.embeddings.provider import get_embedding_provider

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and embedding provider."""
    settings = get_settings()

    # Initialize database
    init_engine(settings)
    engine = get_engine()

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")

    # Initialize embedding provider
    embedding_provider = get_embedding_provider(settings)
    set_embedding_provider(embedding_provider)
    init_routes(settings, embedding_provider)

    logger.info(
        "Embedding provider initialized: %s (%s)",
        settings.EMBEDDING_PROVIDER,
        settings.EMBEDDING_MODEL,
    )

    yield

    # Cleanup
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Sobriquets",
    description="Personal knowledge wiki API",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
