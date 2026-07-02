# classifier/rules.py
from typing import Tuple, Dict, List, Optional, Any, Iterable
import re
from dataclasses import dataclass, field

from models.pdf_file import PDFFile


@dataclass
class ClassificationRule:
    """Represents a single classification rule."""
    category: str
    keywords: List[str]
    weight: float = 1.0
    case_sensitive: bool = False


@dataclass
class ClassificationResult:
    """Structured classification output with backward-compatible tuple behavior."""
    category: str
    subcategory: Optional[str]
    confidence: float
    reasoning: Dict[str, Any]
    topics: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    def __iter__(self) -> Iterable[Any]:
        return iter((self.category, self.confidence, self.reasoning))

    def __getitem__(self, index: int) -> Any:
        if index == 0:
            return self.category
        if index == 1:
            return self.confidence
        if index == 2:
            return self.reasoning
        raise IndexError("ClassificationResult index out of range")

    def __len__(self) -> int:
        return 3


class RuleClassifier:
    """
    Classifies PDFs based on filename, metadata, and first page text.
    
    Complexity: O(n * m) where n is number of rules and m is length of text.
    For typical PDFs with 50-100 keywords and ~2000 chars of text, this is O(50*2000) = ~100k operations per PDF.
    
    Performance optimizations:
    - Precompile regex patterns
    - Early termination when high confidence is achieved
    - Cache compiled patterns
    """
    
    def __init__(self):
        """Initialize the classifier with hardcoded rules."""
        self.rules = self._initialize_rules()
        self.subcategory_map = self._initialize_subcategory_map()
        self._compiled_patterns = {}
        self._compile_patterns()
    
    def _initialize_rules(self) -> List[ClassificationRule]:
        """Initialize classification rules from the specification."""
        rules_data = {
            "Bill": ["invoice", "gst", "total", "amount", "payment", "receipt", "tax", "bill"],
            "Ticket": ["boarding", "flight", "seat", "ticket", "passenger", "gate", "departure"],
            "CV": ["resume", "skills", "experience", "education", "curriculum", "vitae", "cv"],
            "Thesis": ["dissertation", "university", "thesis", "phd", "master", "defense", "academic"],
            "Research": ["abstract", "doi", "ieee", "conference", "journal", "research", "paper"],
            "Book": ["chapter", "table of contents", "preface", "bibliography", "index", "publisher"],
        }
        
        rules = []
        for category, keywords in rules_data.items():
            rules.append(ClassificationRule(
                category=category,
                keywords=keywords,
                weight=1.0
            ))
        return rules
    
    def _compile_patterns(self):
        """Precompile regex patterns for all keywords."""
        for rule in self.rules:
            for keyword in rule.keywords:
                pattern_key = (keyword, rule.case_sensitive)
                if pattern_key not in self._compiled_patterns:
                    flags = 0 if rule.case_sensitive else re.IGNORECASE
                    self._compiled_patterns[pattern_key] = re.compile(
                        re.escape(keyword),
                        flags=flags
                    )
    
    def _initialize_subcategory_map(self) -> Dict[str, Dict[str, List[str]]]:
        """Define deeper category subtypes for hierarchical classification."""
        return {
            "Bill": {
                "Tax Document": ["gst", "vat", "tds", "income tax", "tax invoice"],
                "Receipt": ["receipt", "paid", "payment received", "transaction"],
                "Quote": ["quotation", "estimate", "quote", "proforma"],
                "Invoice": ["invoice", "bill to", "due date", "amount due"],
            },
            "Ticket": {
                "Flight": ["boarding", "airline", "flight", "gate", "departure", "arrival", "passenger"],
                "Train": ["rail", "train", "platform", "coach", "pnr"],
                "Bus": ["bus", "coach", "operator", "boarding point"],
                "Event": ["admission", "venue", "event", "show", "concert", "entry pass"],
            },
            "CV": {
                "Resume": ["resume", "curriculum vitae"],
                "Cover Letter": ["cover letter", "dear hiring", "dear recruiter", "i am writing"],
                "Portfolio": ["portfolio", "projects", "github", "behance", "dribbble"],
            },
            "Thesis": {
                "PhD": ["phd", "doctorate", "doctoral", "doctor of philosophy"],
                "Masters": ["master", "msc", "m.tech", "m.s.", "masters of"],
                "Bachelor": ["bachelor", "undergraduate", "b.tech", "b.sc", "b.e."],
            },
            "Research": {
                "Preprint": ["arxiv", "preprint", "submitted to", "under review"],
                "Conference Paper": ["conference", "proceedings", "workshop", "symposium", "acm", "ieee"],
                "Journal Article": ["journal", "doi", "elsevier", "springer", "volume", "issue", "pages"],
            },
            "Book": {
                "Textbook": ["textbook", "exercises", "problems", "solutions", "edition"],
                "Handbook": ["handbook", "reference", "manual", "guide", "compendium"],
                "Novel": ["novel", "fiction", "chapter one", "the end", "prologue", "epilogue"],
                "Technical Manual": ["installation", "configuration", "troubleshooting", "user manual", "operator"],
            },
        }
    
    def classify(self, pdf: PDFFile, text: str = "") -> "ClassificationResult":
        """
        Classify a PDF using rules in order: filename, metadata, first page text.
        
        Args:
            pdf: PDFFile object containing metadata
            text: First page text content (optional)
            
        Returns:
            Tuple of (category, confidence, debug_info)
            
        Complexity: O(r * (f + m + t)) where:
            r = number of rules (6)
            f = filename length (~50 chars)
            m = metadata fields (4 fields)
            t = text length (~2000 chars)
            
        Optimization: Uses early termination when confidence >= 0.8
        """
        debug_info = {
            "filename_matches": [],
            "metadata_matches": [],
            "text_matches": [],
            "scores": {}
        }
        
        category_scores = {}
        
        # 1. Check filename
        if pdf.filename:
            self._check_text(pdf.filename, category_scores, debug_info["filename_matches"])
        
        # 2. Check metadata fields
        metadata_fields = [pdf.title, pdf.author, pdf.subject, pdf.keywords]
        for field in metadata_fields:
            if field:
                self._check_text(field, category_scores, debug_info["metadata_matches"])
        
        # 3. Check first page text
        if text:
            self._check_text(text, category_scores, debug_info["text_matches"])
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores, key=lambda k: category_scores[k])
            max_score = category_scores[best_category]
            
            total_matches = (
                debug_info["filename_matches"] +
                debug_info["metadata_matches"] +
                debug_info["text_matches"]
            )
            matched_keywords = list(dict.fromkeys(total_matches))
            subcategory = self._derive_subcategory(best_category, matched_keywords)
            confidence = min(1.0, max_score / (1.0 + len(total_matches) * 0.1))
            debug_info["scores"] = category_scores

            return ClassificationResult(
                category=best_category,
                subcategory=subcategory,
                confidence=confidence,
                reasoning=debug_info,
                topics=matched_keywords,
                keywords=matched_keywords,
            )

        debug_info["scores"] = category_scores
        return ClassificationResult(
            category="Unknown",
            subcategory=None,
            confidence=0.0,
            reasoning=debug_info,
            topics=[],
            keywords=[],
        )
    
    def _check_text(self, text: str, scores: Dict[str, float], matches: List[str]):
        """
        Check text against all rules and update scores.
        
        Complexity: O(r * patterns) where r is number of rules and patterns is number of keywords per rule.
        """
        text_lower = text.lower()
        
        for rule in self.rules:
            rule_score = 0
            for keyword in rule.keywords:
                pattern = self._compiled_patterns.get((keyword, rule.case_sensitive))
                if not pattern:
                    continue
                
                if pattern.search(text_lower):
                    rule_score += 1
                    if keyword not in matches:
                        matches.append(keyword)
            
            if rule_score > 0:
                # Weighted score based on number of matches
                scores[rule.category] = scores.get(rule.category, 0) + (rule_score * rule.weight)

    def _derive_subcategory(self, category: str, matches: List[str]) -> Optional[str]:
        """Return the best matching subcategory for the chosen category."""
        if category not in self.subcategory_map:
            return None

        subcategories = self.subcategory_map[category]
        for subcategory, keywords in subcategories.items():
            for match in matches:
                if match in keywords:
                    return subcategory
        return None
    
    def add_rule(self, category: str, keywords: List[str], weight: float = 1.0, case_sensitive: bool = False):
        """
        Add a custom classification rule.
        
        Complexity: O(k) where k is number of keywords.
        """
        rule = ClassificationRule(category, keywords, weight, case_sensitive)
        self.rules.append(rule)
        # Recompile patterns for new keywords
        for keyword in keywords:
            pattern_key = (keyword, case_sensitive)
            if pattern_key not in self._compiled_patterns:
                flags = 0 if case_sensitive else re.IGNORECASE
                self._compiled_patterns[pattern_key] = re.compile(
                    re.escape(keyword),
                    flags=flags
                )