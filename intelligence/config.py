from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeterministicWeights(BaseModel):
    filename: float = 0.20
    title: float = 0.25
    author: float = 0.15
    publisher: float = 0.05
    keywords: float = 0.10
    year: float = 0.05
    page_count: float = 0.05
    location: float = 0.05
    hash: float = 0.10

    def sum(self) -> float:
        return sum(v for v in self.dict().values())


class EmbeddingConfig(BaseModel):
    enabled: bool = False
    provider: str = "sentence-transformers/all-MiniLM-L6-v2"  # or "openai", "ollama", "instructor"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    cache_embeddings: bool = True
    batch_size: int = 32


class ClusteringConfig(BaseModel):
    algorithm: str = "dbscan"  # "dbscan", "agglomerative", "kmeans"
    dbscan_eps: float = 0.75
    min_samples: int = 3
    use_sparse: bool = True
    top_k_neighbours: int = 50  # for sparse approximation
    agglomerative_n_clusters: Optional[int] = None


class ConfidenceConfig(BaseModel):
    threshold: int = 60  # minimum score to report


class InsightsConfig(BaseModel):
    enabled: bool = True
    detectors: List[str] = Field(
        default=[
            "hidden_collections",
            "misplaced_files",
            "duplicate_folders",
            "fragmented_library",
            "largest_collections",
            "recently_growing",
            "author_concentration",
            "books_without_metadata",
            "old_forgotten_folders",
            "research_trends",
        ]
    )


class PerformanceConfig(BaseModel):
    max_workers: int = 4
    batch_size: int = 100
    similarity_batch_size: int = 5000


class IAMConfig(BaseModel):
    enabled: bool = True
    similarity_deterministic_weights: DeterministicWeights = DeterministicWeights()
    embedding: EmbeddingConfig = EmbeddingConfig()
    clustering: ClusteringConfig = ClusteringConfig()
    confidence: ConfidenceConfig = ConfidenceConfig()
    insights: InsightsConfig = InsightsConfig()
    performance: PerformanceConfig = PerformanceConfig()