from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from scipy.spatial.distance import squareform
from .models import PDFMetadata, ClusterAssignment
from .config import IAMConfig


class ClusteringAlgorithm(ABC):
    @abstractmethod
    def cluster(self, docs: List[PDFMetadata], similarity_matrix: np.ndarray) -> List[ClusterAssignment]:
        pass


class DBSCANClustering(ClusteringAlgorithm):
    def __init__(self, eps: float = 0.75, min_samples: int = 3):
        self.eps = eps
        self.min_samples = min_samples

    def cluster(self, docs: List[PDFMetadata], similarity_matrix: np.ndarray) -> List[ClusterAssignment]:
        # Convert similarity to distance (1 - similarity)
        distances = 1 - similarity_matrix
        np.fill_diagonal(distances, 0)

        clustering = DBSCAN(eps=1 - self.eps, min_samples=self.min_samples, metric="precomputed")
        labels = clustering.fit_predict(distances)

        assignments = []
        for i, (doc, label) in enumerate(zip(docs, labels)):
            assignments.append(
                ClusterAssignment(
                    pdf_id=doc.id,
                    cluster_id=int(label),
                    algorithm="dbscan",
                    parameters={"eps": self.eps, "min_samples": self.min_samples}
                )
            )
        return assignments


class AgglomerativeClusteringAlgorithm(ClusteringAlgorithm):
    def __init__(self, n_clusters: int = 10, linkage: str = "average"):
        self.n_clusters = n_clusters
        self.linkage = linkage

    def cluster(self, docs: List[PDFMetadata], similarity_matrix: np.ndarray) -> List[ClusterAssignment]:
        distances = 1 - similarity_matrix
        np.fill_diagonal(distances, 0)

        clustering = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            metric="precomputed",
            linkage=self.linkage
        )
        labels = clustering.fit_predict(distances)

        assignments = []
        for i, (doc, label) in enumerate(zip(docs, labels)):
            assignments.append(
                ClusterAssignment(
                    pdf_id=doc.id,
                    cluster_id=int(label),
                    algorithm="agglomerative",
                    parameters={"n_clusters": self.n_clusters, "linkage": self.linkage}
                )
            )
        return assignments


def get_clustering_algorithm(config: IAMConfig) -> ClusteringAlgorithm:
    algo = config.clustering.algorithm
    if algo == "dbscan":
        return DBSCANClustering(eps=config.clustering.dbscan_eps, min_samples=config.clustering.min_samples)
    elif algo == "agglomerative":
        return AgglomerativeClusteringAlgorithm(
            n_clusters=config.clustering.agglomerative_n_clusters or 10
        )
    else:
        raise ValueError(f"Unsupported clustering algorithm: {algo}")