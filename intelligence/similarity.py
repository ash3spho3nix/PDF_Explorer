from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from .models import PDFMetadata
from .config import IAMConfig
import hashlib
import json


class SimilarityStrategy(ABC):
    @abstractmethod
    def compute(self, doc1: PDFMetadata, doc2: PDFMetadata) -> float:
        pass


class DeterministicSimilarity(SimilarityStrategy):
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights
        self._tfidf = None
        self._doc_texts = {}

    def _text_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        return fuzz.token_sort_ratio(text1, text2) / 100.0

    def _author_similarity(self, auth1: str, auth2: str) -> float:
        if not auth1 or not auth2:
            return 0.0
        set1 = set(auth1.lower().split(","))
        set2 = set(auth2.lower().split(","))
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    def _keyword_similarity(self, kw1: List[str], kw2: List[str]) -> float:
        if not kw1 or not kw2:
            return 0.0
        set1 = set(k.lower() for k in kw1)
        set2 = set(k.lower() for k in kw2)
        return len(set1 & set2) / len(set1 | set2)

    def _year_similarity(self, y1: Optional[int], y2: Optional[int]) -> float:
        if y1 is None or y2 is None:
            return 0.0
        diff = abs(y1 - y2)
        if diff > 50:
            return 0.0
        return 1.0 - (diff / 50.0)

    def _page_count_similarity(self, pc1: Optional[int], pc2: Optional[int]) -> float:
        if pc1 is None or pc2 is None or pc1 == 0 or pc2 == 0:
            return 0.0
        ratio = min(pc1, pc2) / max(pc1, pc2)
        return ratio

    def _location_similarity(self, path1: str, path2: str) -> float:
        parts1 = path1.split("/")
        parts2 = path2.split("/")
        common = 0
        for p1, p2 in zip(parts1, parts2):
            if p1 == p2:
                common += 1
            else:
                break
        max_depth = max(len(parts1), len(parts2))
        return common / max_depth if max_depth > 0 else 0.0

    def compute(self, doc1: PDFMetadata, doc2: PDFMetadata) -> float:
        if doc1.id == doc2.id:
            return 1.0

        # Hash match
        if doc1.file_hash and doc2.file_hash and doc1.file_hash == doc2.file_hash:
            return 1.0

        scores = {}
        scores["filename"] = self._text_similarity(doc1.filename, doc2.filename)
        scores["title"] = self._text_similarity(doc1.title or "", doc2.title or "")
        scores["author"] = self._author_similarity(doc1.author or "", doc2.author or "")
        scores["publisher"] = self._text_similarity(doc1.publisher or "", doc2.publisher or "")
        scores["keywords"] = self._keyword_similarity(doc1.keywords or [], doc2.keywords or [])
        scores["year"] = self._year_similarity(doc1.year, doc2.year)
        scores["page_count"] = self._page_count_similarity(doc1.page_count, doc2.page_count)
        scores["location"] = self._location_similarity(doc1.file_path, doc2.file_path)
        # hash match is handled above

        total = 0.0
        for key, weight in self.weights.items():
            if key == "hash":
                continue  # already handled
            total += weight * scores.get(key, 0.0)

        return min(1.0, total)


class EmbeddingSimilarity(SimilarityStrategy):
    def __init__(self, provider, cache_conn=None):
        self.provider = provider
        self.cache_conn = cache_conn
        self._embeddings_cache = {}

    def _get_embedding(self, doc: PDFMetadata) -> np.ndarray:
        if doc.id in self._embeddings_cache:
            return self._embeddings_cache[doc.id]

        # Check DB cache
        if self.cache_conn:
            cursor = self.cache_conn.cursor()
            cursor.execute(
                "SELECT embedding FROM iam_similarity WHERE pdf_id_1 = ? AND pdf_id_2 = ? AND strategy = 'embedding'",
                (doc.id, doc.id)
            )
            row = cursor.fetchone()
            if row and row[0]:
                import pickle
                emb = pickle.loads(row[0])
                self._embeddings_cache[doc.id] = emb
                return emb

        # Generate text
        parts = []
        if doc.title:
            parts.append(doc.title)
        if doc.author:
            parts.append(doc.author)
        if doc.keywords:
            parts.append(" ".join(doc.keywords))
        text = " ".join(parts) if parts else doc.filename

        emb = self.provider.encode([text])[0]

        # Cache in DB
        if self.cache_conn:
            import pickle
            cursor = self.cache_conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO iam_similarity (pdf_id_1, pdf_id_2, strategy, embedding) VALUES (?, ?, ?, ?)",
                (doc.id, doc.id, "embedding", pickle.dumps(emb))
            )
            self.cache_conn.commit()

        self._embeddings_cache[doc.id] = emb
        return emb

    def compute(self, doc1: PDFMetadata, doc2: PDFMetadata) -> float:
        if doc1.id == doc2.id:
            return 1.0
        emb1 = self._get_embedding(doc1)
        emb2 = self._get_embedding(doc2)
        # cosine similarity
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))