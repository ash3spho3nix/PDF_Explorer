from typing import List, Dict, Any
import networkx as nx
from .models import PDFMetadata, SimilarityPair, GraphEdge, ClusterAssignment


class RelationshipGraph:
    def __init__(self):
        self.graph = nx.Graph()

    def add_pdf_nodes(self, docs: List[PDFMetadata]):
        for doc in docs:
            self.graph.add_node(
                doc.id,
                title=doc.title or doc.filename,
                author=doc.author,
                publisher=doc.publisher,
                category=doc.category,
                year=doc.year,
                file_path=doc.file_path
            )

    def add_similarity_edges(self, pairs: List[SimilarityPair], threshold: float = 0.6):
        for pair in pairs:
            if pair.score >= threshold:
                self.graph.add_edge(
                    pair.pdf_id_1,
                    pair.pdf_id_2,
                    type="similarity",
                    weight=pair.score,
                    strategy=pair.strategy
                )

    def add_metadata_edges(self, docs: List[PDFMetadata]):
        # Same author
        for i, d1 in enumerate(docs):
            for d2 in docs[i+1:]:
                if d1.author and d2.author and d1.author == d2.author:
                    self.graph.add_edge(d1.id, d2.id, type="same_author", weight=1.0)
                if d1.publisher and d2.publisher and d1.publisher == d2.publisher:
                    self.graph.add_edge(d1.id, d2.id, type="same_publisher", weight=1.0)
                # Same folder (parent directory)
                folder1 = "/".join(d1.file_path.split("/")[:-1])
                folder2 = "/".join(d2.file_path.split("/")[:-1])
                if folder1 and folder2 and folder1 == folder2:
                    self.graph.add_edge(d1.id, d2.id, type="same_folder", weight=1.0)

    def add_cluster_edges(self, assignments: List[ClusterAssignment]):
        # Group by cluster
        clusters = {}
        for assign in assignments:
            if assign.cluster_id != -1:
                clusters.setdefault(assign.cluster_id, []).append(assign.pdf_id)
        for cluster_id, pdf_ids in clusters.items():
            for i in range(len(pdf_ids)):
                for j in range(i+1, len(pdf_ids)):
                    self.graph.add_edge(pdf_ids[i], pdf_ids[j], type="same_topic", weight=0.8)

    def get_edges(self) -> List[GraphEdge]:
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(
                GraphEdge(
                    source=u,
                    target=v,
                    edge_type=data.get("type", "unknown"),
                    weight=data.get("weight", 0.5)
                )
            )
        return edges

    def to_networkx(self) -> nx.Graph:
        return self.graph