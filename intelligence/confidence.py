from typing import List, Dict, Any
from .models import PDFMetadata, ConfidenceScore


class ConfidenceScorer:
    """Rule-based explainable confidence for each category."""

    CATEGORY_RULES = {
        "Research Paper": [
            ("DOI present", lambda d: bool(d.title and "doi.org" in d.title.lower()), 25),
            ("References section", lambda d: bool(d.keywords and any("reference" in k.lower() for k in d.keywords)), 20),
            ("Typical page count (5-30)", lambda d: d.page_count and 5 <= d.page_count <= 30, 10),
            ("Conference keywords", lambda d: bool(d.keywords and any(
                k.lower() in ["conference", "proceedings", "workshop", "symposium"] for k in d.keywords)), 15),
            ("Multiple authors", lambda d: d.author and len(d.author.split(",")) >= 2, 10),
            ("Abstract-like title", lambda d: d.title and len(d.title.split()) > 5, 5),
        ],
        "Book": [
            ("ISBN present", lambda d: bool(d.title and "isbn" in d.title.lower()), 30),
            ("Large page count", lambda d: d.page_count and d.page_count > 100, 20),
            ("Publisher field", lambda d: bool(d.publisher), 15),
            ("Single author or editor", lambda d: d.author and len(d.author.split(",")) <= 2, 10),
            ("Year present", lambda d: d.year is not None, 10),
            ("Book-like title", lambda d: d.title and len(d.title.split()) <= 5, 5),
        ],
        "Report": [
            ("Report keyword", lambda d: bool(d.keywords and any(
                k.lower() in ["report", "annual", "quarterly", "white paper"] for k in d.keywords)), 25),
            ("Organisation author", lambda d: d.author and "university" in d.author.lower() or "inc" in d.author.lower(), 15),
            ("Page count 20-100", lambda d: d.page_count and 20 <= d.page_count <= 100, 10),
            ("Date in filename", lambda d: any(c.isdigit() for c in d.filename), 10),
            ("Formal structure", lambda d: bool(d.title and "report" in d.title.lower()), 20),
        ],
        "Thesis / Dissertation": [
            ("Thesis keyword", lambda d: bool(d.title and any(
                w in d.title.lower() for w in ["thesis", "dissertation", "phd"])), 30),
            ("University author", lambda d: d.author and any(
                w in d.author.lower() for w in ["university", "college", "institute"]), 15),
            ("Page count > 50", lambda d: d.page_count and d.page_count > 50, 15),
            ("Year in title", lambda d: d.title and any(c.isdigit() for c in d.title), 10),
        ],
        "Manual / Guide": [
            ("Guide keyword", lambda d: bool(d.title and any(
                w in d.title.lower() for w in ["manual", "guide", "handbook", "user"])), 30),
            ("Step by step", lambda d: d.keywords and any(
                k.lower() in ["tutorial", "how-to", "instructions"] for k in d.keywords), 20),
            ("Page count 10-200", lambda d: d.page_count and 10 <= d.page_count <= 200, 10),
        ],
        "Unknown": [
            ("Default", lambda d: True, 1),
        ]
    }

    def score(self, doc: PDFMetadata, category: str) -> ConfidenceScore:
        rules = self.CATEGORY_RULES.get(category, self.CATEGORY_RULES["Unknown"])
        total = 0
        reasons = []
        for reason, condition, weight in rules:
            if condition(doc):
                total += weight
                reasons.append(reason)
        total = min(100, total)

        return ConfidenceScore(
            pdf_id=doc.id,
            category=category,
            confidence=total,
            reasons=reasons
        )

    def score_all(self, docs: List[PDFMetadata], categories: List[str]) -> List[ConfidenceScore]:
        scores = []
        for doc in docs:
            # Use existing category if available, else check all
            cats = [doc.category] if doc.category else categories
            for cat in cats:
                scores.append(self.score(doc, cat))
        return scores