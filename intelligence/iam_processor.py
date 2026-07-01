from typing import List, Optional
import sqlite3
import logging
from datetime import datetime
import numpy as np

from .config import IAMConfig
from .models import PDFMetadata, SimilarityPair, ClusterAssignment, ConfidenceScore, GraphEdge, Insight
from .utils import ensure_db_tables, parallel_map, batched
from .embeddings import get_embedding_provider
from .similarity import DeterministicSimilarity, EmbeddingSimilarity
from .clustering import get_clustering_algorithm
from .confidence import ConfidenceScorer
from .graph import RelationshipGraph
from .insights import InsightDetector

logger = logging.getLogger(__name__)


class IAMProcessor:
    def __init__(self, db_path: str, config: Optional[IAMConfig] = None):
        self.db_path = db_path
        self.config = config or IAMConfig()
        self.conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            ensure_db_tables(self.conn)
        return self.conn

    def analyze(self, docs: List[PDFMetadata]) -> dict:
        """
        Main entry point. Returns a dictionary with all IAM outputs.
        """
        if not self.config.enabled or not docs:
            return {}

        logger.info(f"IAM analyzing {len(docs)} PDFs...")
        results = {
            "similarities": [],
            "clusters": [],
            "confidences": [],
            "graph_edges": [],
            "insights": [],
            "stats": {},
        }

        conn = self._get_conn()
        cursor = conn.cursor()

        # ---- 1. Similarity ----
        similarity_strategy = DeterministicSimilarity(
            self.config.similarity_deterministic_weights.dict()
        )

        # Compute pairwise (only for new docs)
        # For performance, we only compute for documents that don't have cached similarities
        # Simple approach: compute all pairs for small collections, else batch
        N = len(docs)
        if N <= 1:
            return results

        logger.info("Computing deterministic similarities...")
        pairs = []
        # Use parallel batch processing
        doc_ids = [d.id for d in docs]
        id_to_doc = {d.id: d for d in docs}

        # Check which pairs already exist
        existing = set()
        if N < 5000:
            # Full pairwise
            all_pairs = [(i, j) for i in range(N) for j in range(i+1, N)]
            for i, j in all_pairs:
                d1, d2 = docs[i], docs[j]
                # Check cache
                cursor.execute(
                    "SELECT score FROM iam_similarity WHERE pdf_id_1 = ? AND pdf_id_2 = ? AND strategy = 'deterministic'",
                    (d1.id, d2.id)
                )
                row = cursor.fetchone()
                if row:
                    pairs.append(SimilarityPair(
                        pdf_id_1=d1.id,
                        pdf_id_2=d2.id,
                        strategy="deterministic",
                        score=row[0]
                    ))
                else:
                    score = similarity_strategy.compute(d1, d2)
                    pairs.append(SimilarityPair(
                        pdf_id_1=d1.id,
                        pdf_id_2=d2.id,
                        strategy="deterministic",
                        score=score
                    ))
                    # Insert into DB
                    cursor.execute(
                        "INSERT OR REPLACE INTO iam_similarity (pdf_id_1, pdf_id_2, strategy, score) VALUES (?, ?, ?, ?)",
                        (d1.id, d2.id, "deterministic", score)
                    )
            conn.commit()
        else:
            # For large N, use sparse: only compute top-k nearest for each doc
            # We'll compute similarities in batches and keep only high scores (>0.6)
            logger.warning("Large collection: using sparse similarity (top-k neighbours)")
            from sklearn.neighbors import NearestNeighbors
            # Build feature matrix from deterministic features (simplified)
            features = []
            for doc in docs:
                f = [
                    len(doc.filename),
                    len(doc.title) if doc.title else 0,
                    len(doc.author) if doc.author else 0,
                    doc.year or 0,
                    doc.page_count or 0,
                    len(doc.keywords) if doc.keywords else 0
                ]
                features.append(f)
            features = np.array(features)
            nn = NearestNeighbors(n_neighbors=min(50, N), metric="euclidean")
            nn.fit(features)
            distances, indices = nn.kneighbors(features)

            for i in range(N):
                for j in indices[i]:
                    if j <= i:
                        continue
                    d1, d2 = docs[i], docs[j]
                    score = similarity_strategy.compute(d1, d2)
                    if score > 0.5:  # keep only meaningful
                        pairs.append(SimilarityPair(
                            pdf_id_1=d1.id,
                            pdf_id_2=d2.id,
                            strategy="deterministic",
                            score=score
                        ))
                        cursor.execute(
                            "INSERT OR REPLACE INTO iam_similarity (pdf_id_1, pdf_id_2, strategy, score) VALUES (?, ?, ?, ?)",
                            (d1.id, d2.id, "deterministic", score)
                        )
            conn.commit()

        results["similarities"] = pairs

        # ---- 2. Embedding (optional) ----
        if self.config.embedding.enabled:
            logger.info("Computing embedding similarities...")
            provider = get_embedding_provider(self.config)
            if provider:
                emb_strategy = EmbeddingSimilarity(provider, conn)
                # Compute embeddings for all docs (cached)
                for i in range(N):
                    for j in range(i+1, N):
                        d1, d2 = docs[i], docs[j]
                        cursor.execute(
                            "SELECT score FROM iam_similarity WHERE pdf_id_1 = ? AND pdf_id_2 = ? AND strategy = 'embedding'",
                            (d1.id, d2.id)
                        )
                        if not cursor.fetchone():
                            score = emb_strategy.compute(d1, d2)
                            cursor.execute(
                                "INSERT OR REPLACE INTO iam_similarity (pdf_id_1, pdf_id_2, strategy, score) VALUES (?, ?, ?, ?)",
                                (d1.id, d2.id, "embedding", score)
                            )
                conn.commit()

        # ---- 3. Build similarity matrix for clustering ----
        # Use deterministic scores; fallback to embedding if enabled
        logger.info("Building similarity matrix for clustering...")
        sim_matrix = np.zeros((N, N))
        for pair in pairs:
            i = doc_ids.index(pair.pdf_id_1)
            j = doc_ids.index(pair.pdf_id_2)
            sim_matrix[i, j] = pair.score
            sim_matrix[j, i] = pair.score
        np.fill_diagonal(sim_matrix, 1.0)

        # ---- 4. Clustering ----
        logger.info("Running clustering...")
        clustering_algo = get_clustering_algorithm(self.config)
        assignments = clustering_algo.cluster(docs, sim_matrix)
        results["clusters"] = assignments

        # Store clusters in DB
        cursor.execute("DELETE FROM iam_clusters")
        for assign in assignments:
            cursor.execute(
                "INSERT OR REPLACE INTO iam_clusters (pdf_id, cluster_id, algorithm, parameters) VALUES (?, ?, ?, ?)",
                (assign.pdf_id, assign.cluster_id, assign.algorithm, str(assign.parameters))
            )
        conn.commit()

        # ---- 5. Confidence ----
        logger.info("Computing confidence scores...")
        scorer = ConfidenceScorer()
        categories = list(scorer.CATEGORY_RULES.keys())
        confidences = scorer.score_all(docs, categories)
        results["confidences"] = confidences
        cursor.execute("DELETE FROM iam_confidence")
        for conf in confidences:
            cursor.execute(
                "INSERT OR REPLACE INTO iam_confidence (pdf_id, category, confidence, reasons) VALUES (?, ?, ?, ?)",
                (conf.pdf_id, conf.category, conf.confidence, ",".join(conf.reasons))
            )
        conn.commit()

        # ---- 6. Graph ----
        logger.info("Building relationship graph...")
        graph = RelationshipGraph()
        graph.add_pdf_nodes(docs)
        graph.add_similarity_edges(pairs, threshold=0.6)
        graph.add_metadata_edges(docs)
        graph.add_cluster_edges(assignments)
        graph_edges = graph.get_edges()
        results["graph_edges"] = graph_edges

        cursor.execute("DELETE FROM iam_graph_edges")
        for edge in graph_edges:
            cursor.execute(
                "INSERT OR REPLACE INTO iam_graph_edges (source, target, edge_type, weight) VALUES (?, ?, ?, ?)",
                (edge.source, edge.target, edge.edge_type, edge.weight)
            )
        conn.commit()

        # ---- 7. Insights ----
        if self.config.insights.enabled:
            logger.info("Generating insights...")
            detector = InsightDetector(docs, graph, assignments)
            insights = detector.detect_all(self.config.insights.detectors)
            results["insights"] = insights

            cursor.execute("DELETE FROM iam_insights")
            for ins in insights:
                cursor.execute(
                    """INSERT INTO iam_insights 
                       (type, severity, title, description, affected_pdf_ids, extra_data) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (ins.type, ins.severity, ins.title, ins.description,
                     ",".join(map(str, ins.affected_pdf_ids)),
                     str(ins.extra_data))
                )
            conn.commit()

        # ---- Stats ----
        results["stats"] = {
            "total_pdfs": N,
            "clusters": len(set(a.cluster_id for a in assignments if a.cluster_id != -1)),
            "noise_pdfs": sum(1 for a in assignments if a.cluster_id == -1),
            "similarity_pairs": len(pairs),
            "insights": len(insights),
        }

        logger.info(f"IAM analysis complete: {results['stats']}")
        return results