from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
import hashlib
import sqlite3
import json


class EmbeddingProvider(ABC):
    """Abstract base for embedding generation."""

    @abstractmethod
    def encode(self, texts: List[str]) -> np.ndarray:
        """Return a numpy array of shape (len(texts), embedding_dim)."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def dimension(self) -> int:
        # all-MiniLM-L6-v2 = 384
        return 384

    def encode(self, texts: List[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model.encode(texts, convert_to_numpy=True)


class OpenAIProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model = model

    @property
    def dimension(self) -> int:
        return 1536

    def encode(self, texts: List[str]) -> np.ndarray:
        import openai
        openai.api_key = self.api_key
        response = openai.Embedding.create(input=texts, model=self.model)
        embeddings = [item["embedding"] for item in response["data"]]
        return np.array(embeddings, dtype=np.float32)


class OllamaProvider(EmbeddingProvider):
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    @property
    def dimension(self) -> int:
        return 768  # approximate, may vary

    def encode(self, texts: List[str]) -> np.ndarray:
        import requests
        embeddings = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return np.array(embeddings, dtype=np.float32)


def get_embedding_provider(config) -> Optional[EmbeddingProvider]:
    if not config.embedding.enabled:
        return None

    provider_name = config.embedding.provider
    if provider_name.startswith("sentence-transformers/"):
        return SentenceTransformerProvider(model_name=provider_name)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=config.embedding.api_key)
    elif provider_name == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider_name}")