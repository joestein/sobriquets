import asyncio

from sobriquets.embeddings.provider import EmbeddingProvider


class SentenceTransformerProvider(EmbeddingProvider):
    """Local sentence-transformers embedding provider."""

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using sentence-transformers."""
        model = self._load_model()
        embeddings = await asyncio.to_thread(
            model.encode, texts, normalize_embeddings=True
        )
        return [embedding.tolist() for embedding in embeddings]

    @property
    def dimension(self) -> int:
        return self._dimension
