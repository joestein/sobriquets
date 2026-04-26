from abc import ABC, abstractmethod

from sobriquets.config import Settings


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Factory function to create the configured embedding provider."""
    if settings.EMBEDDING_PROVIDER == "sentence_transformers":
        from sobriquets.embeddings.sentence_transformers import (
            SentenceTransformerProvider,
        )

        return SentenceTransformerProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
    elif settings.EMBEDDING_PROVIDER == "openai":
        from sobriquets.embeddings.openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
            api_key=settings.OPENAI_API_KEY,
            api_base=settings.OPENAI_API_BASE,
        )
    else:
        raise ValueError(
            f"Unknown embedding provider: {settings.EMBEDDING_PROVIDER}. "
            "Use 'sentence_transformers' or 'openai'."
        )
