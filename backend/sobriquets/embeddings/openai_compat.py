import httpx

from sobriquets.embeddings.provider import EmbeddingProvider


class OpenAICompatProvider(EmbeddingProvider):
    """OpenAI-compatible API embedding provider."""

    def __init__(
        self,
        model_name: str,
        dimension: int,
        api_key: str,
        api_base: str,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via OpenAI-compatible API."""
        url = f"{self._api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model_name,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]

    @property
    def dimension(self) -> int:
        return self._dimension
