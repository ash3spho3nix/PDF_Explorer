import multiprocessing
import sqlite3
import json
from typing import List, Any, Callable, Iterable
from functools import partial


def parallel_map(func: Callable, items: List[Any], max_workers: int = 4) -> List[Any]:
    """Run func in parallel over items, preserving order."""
    if max_workers <= 1:
        return [func(item) for item in items]
    with multiprocessing.Pool(max_workers) as pool:
        return pool.map(func, items)


def batched(iterable: Iterable, n: int):
    """Yield successive n-sized chunks."""
    from itertools import islice
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            break
        yield batch


def dict_factory(cursor, row):
    """Convert SQLite row to dict."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def ensure_db_tables(conn: sqlite3.Connection):
    """Create IAM-specific tables if they don't exist."""
    cursor = conn.cursor()
    cursor.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS iam_similarity (
            pdf_id_1 INTEGER,
            pdf_id_2 INTEGER,
            strategy TEXT,
            score REAL,
            embedding BLOB,
            PRIMARY KEY (pdf_id_1, pdf_id_2, strategy)
        );
        CREATE INDEX IF NOT EXISTS idx_iam_sim_pdf1 ON iam_similarity(pdf_id_1);
        CREATE INDEX IF NOT EXISTS idx_iam_sim_score ON iam_similarity(score);

        CREATE TABLE IF NOT EXISTS iam_clusters (
            pdf_id INTEGER PRIMARY KEY,
            cluster_id INTEGER,
            algorithm TEXT,
            parameters TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_iam_cluster_id ON iam_clusters(cluster_id);

        CREATE TABLE IF NOT EXISTS iam_confidence (
            pdf_id INTEGER,
            category TEXT,
            confidence INTEGER,
            reasons TEXT,
            PRIMARY KEY (pdf_id, category)
        );

        CREATE TABLE IF NOT EXISTS iam_graph_edges (
            source INTEGER,
            target INTEGER,
            edge_type TEXT,
            weight REAL,
            PRIMARY KEY (source, target, edge_type)
        );
        CREATE INDEX IF NOT EXISTS idx_iam_edge_source ON iam_graph_edges(source);
        CREATE INDEX IF NOT EXISTS idx_iam_edge_target ON iam_graph_edges(target);

        CREATE TABLE IF NOT EXISTS iam_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            severity TEXT,
            title TEXT,
            description TEXT,
            affected_pdf_ids TEXT,
            extra_data TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()