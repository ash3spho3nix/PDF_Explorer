import os
from storage.cache import CacheManager
from analyzer.statistics import StatisticsAnalyzer

_db_path = os.environ.get("PDF_DB", "pdf_inventory.db")
cache = CacheManager(db_path=_db_path)
stats_analyzer = StatisticsAnalyzer()


def get_stats():
    pdfs = cache.get_all_pdfs()
    return stats_analyzer.compute(pdfs)
