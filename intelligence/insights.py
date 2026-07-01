from typing import List, Dict, Any, Set
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import networkx as nx
from .models import PDFMetadata, Insight, GraphEdge, ClusterAssignment
from .graph import RelationshipGraph


class InsightDetector:
    def __init__(self, docs: List[PDFMetadata], graph: RelationshipGraph, assignments: List[ClusterAssignment]):
        self.docs = docs
        self.graph = graph
        self.assignments = assignments
        self.doc_map = {d.id: d for d in docs}

    def detect_all(self, enabled_detectors: List[str]) -> List[Insight]:
        findings = []
        detectors = {
            "hidden_collections": self.hidden_collections,
            "misplaced_files": self.misplaced_files,
            "duplicate_folders": self.duplicate_folders,
            "fragmented_library": self.fragmented_library,
            "largest_collections": self.largest_collections,
            "recently_growing": self.recently_growing,
            "author_concentration": self.author_concentration,
            "books_without_metadata": self.books_without_metadata,
            "old_forgotten_folders": self.old_forgotten_folders,
            "research_trends": self.research_trends,
        }
        for name in enabled_detectors:
            if name in detectors:
                try:
                    findings.extend(detectors[name]())
                except Exception as e:
                    # Log but continue
                    pass
        return findings

    def hidden_collections(self) -> List[Insight]:
        # Clusters with >3 docs but no common folder
        cluster_groups = defaultdict(list)
        for assign in self.assignments:
            if assign.cluster_id != -1:
                cluster_groups[assign.cluster_id].append(assign.pdf_id)

        findings = []
        for cid, ids in cluster_groups.items():
            if len(ids) >= 4:
                folders = set()
                for pid in ids:
                    doc = self.doc_map.get(pid)
                    if doc:
                        folders.add("/".join(doc.file_path.split("/")[:-1]))
                if len(folders) > 1:
                    findings.append(Insight(
                        type="hidden_collections",
                        severity="info",
                        title=f"Hidden Collection Detected (Cluster {cid})",
                        description=f"{len(ids)} PDFs appear related but are spread across {len(folders)} different folders.",
                        affected_pdf_ids=ids,
                        extra_data={"folders": list(folders)}
                    ))
        return findings

    def misplaced_files(self) -> List[Insight]:
        # Files that are in a cluster but in a folder that is different from the majority
        cluster_folders = defaultdict(list)
        for assign in self.assignments:
            if assign.cluster_id != -1:
                doc = self.doc_map.get(assign.pdf_id)
                if doc:
                    folder = "/".join(doc.file_path.split("/")[:-1])
                    cluster_folders[assign.cluster_id].append((assign.pdf_id, folder))

        findings = []
        for cid, items in cluster_folders.items():
            if len(items) < 3:
                continue
            folder_counts = Counter([f for _, f in items])
            most_common = folder_counts.most_common(1)[0][0]
            outliers = [pid for pid, f in items if f != most_common]
            if outliers:
                findings.append(Insight(
                    type="misplaced_files",
                    severity="warning",
                    title=f"Misplaced Files in Cluster {cid}",
                    description=f"{len(outliers)} PDFs in this cluster are located outside the main folder '{most_common}'.",
                    affected_pdf_ids=outliers,
                    extra_data={"main_folder": most_common}
                ))
        return findings

    def duplicate_folders(self) -> List[Insight]:
        # Folders with high similarity (>80%) of files
        folder_to_ids = defaultdict(set)
        for doc in self.docs:
            folder = "/".join(doc.file_path.split("/")[:-1])
            folder_to_ids[folder].add(doc.id)

        folders = list(folder_to_ids.keys())
        findings = []
        for i in range(len(folders)):
            for j in range(i+1, len(folders)):
                f1, f2 = folders[i], folders[j]
                set1 = folder_to_ids[f1]
                set2 = folder_to_ids[f2]
                if not set1 or not set2:
                    continue
                overlap = len(set1 & set2) / min(len(set1), len(set2))
                if overlap > 0.8:
                    findings.append(Insight(
                        type="duplicate_folders",
                        severity="warning",
                        title="Duplicate Folders Detected",
                        description=f"Folders '{f1}' and '{f2}' share {int(overlap*100)}% of PDFs.",
                        affected_pdf_ids=list(set1 | set2),
                        extra_data={"folder1": f1, "folder2": f2, "overlap": overlap}
                    ))
        return findings

    def fragmented_library(self) -> List[Insight]:
        # Many small clusters (size < 3)
        cluster_sizes = defaultdict(int)
        for assign in self.assignments:
            if assign.cluster_id != -1:
                cluster_sizes[assign.cluster_id] += 1
        small = [cid for cid, size in cluster_sizes.items() if size < 3]
        if len(small) > 5:
            ids = [assign.pdf_id for assign in self.assignments if assign.cluster_id in small]
            findings.append(Insight(
                type="fragmented_library",
                severity="info",
                title="Fragmented Library",
                description=f"There are {len(small)} small clusters (≤2 PDFs) that might be merged or expanded.",
                affected_pdf_ids=ids[:20],
                extra_data={"small_clusters": small}
            ))
        return findings

    def largest_collections(self) -> List[Insight]:
        cluster_sizes = defaultdict(list)
        for assign in self.assignments:
            if assign.cluster_id != -1:
                cluster_sizes[assign.cluster_id].append(assign.pdf_id)
        top5 = sorted(cluster_sizes.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        findings = []
        for cid, ids in top5:
            if len(ids) >= 3:
                findings.append(Insight(
                    type="largest_collections",
                    severity="info",
                    title=f"Large Collection (Cluster {cid})",
                    description=f"{len(ids)} PDFs form a major collection.",
                    affected_pdf_ids=ids[:10],
                    extra_data={"cluster_id": cid, "size": len(ids)}
                ))
        return findings

    def recently_growing(self) -> List[Insight]:
        # Folders with >20 new files in last 30 days
        from collections import defaultdict
        folder_counts = defaultdict(int)
        for doc in self.docs:
            if doc.modified_time and doc.modified_time > datetime.now() - timedelta(days=30):
                folder = "/".join(doc.file_path.split("/")[:-1])
                folder_counts[folder] += 1
        active = [f for f, cnt in folder_counts.items() if cnt > 20]
        if active:
            ids = [d.id for d in self.docs if "/".join(d.file_path.split("/")[:-1]) in active]
            findings.append(Insight(
                type="recently_growing",
                severity="info",
                title="Recently Growing Folders",
                description=f"{len(active)} folders have added >20 PDFs in the last 30 days.",
                affected_pdf_ids=ids[:10],
                extra_data={"folders": active}
            ))
        return findings

    def author_concentration(self) -> List[Insight]:
        author_count = defaultdict(int)
        for doc in self.docs:
            if doc.author:
                for auth in doc.author.split(","):
                    author_count[auth.strip()] += 1
        top_authors = [a for a, cnt in author_count.items() if cnt > 10]
        if top_authors:
            ids = [d.id for d in self.docs if d.author and any(a in d.author for a in top_authors)]
            findings.append(Insight(
                type="author_concentration",
                severity="info",
                title="Author Concentration",
                description=f"{len(top_authors)} authors appear in more than 10 documents.",
                affected_pdf_ids=ids[:10],
                extra_data={"authors": top_authors[:5]}
            ))
        return findings

    def books_without_metadata(self) -> List[Insight]:
        missing = []
        for doc in self.docs:
            if doc.category and "book" in doc.category.lower():
                if not doc.publisher and not doc.year:
                    missing.append(doc.id)
        if missing:
            findings.append(Insight(
                type="books_without_metadata",
                severity="warning",
                title="Books Lacking Metadata",
                description=f"{len(missing)} books have no publisher or year information.",
                affected_pdf_ids=missing[:20]
            ))
        return findings

    def old_forgotten_folders(self) -> List[Insight]:
        # Folders with no file newer than 2 years
        folder_last = defaultdict(datetime.min)
        for doc in self.docs:
            folder = "/".join(doc.file_path.split("/")[:-1])
            if doc.modified_time and doc.modified_time > folder_last[folder]:
                folder_last[folder] = doc.modified_time
        old = [f for f, dt in folder_last.items() if dt < datetime.now() - timedelta(days=730)]
        if old:
            ids = [d.id for d in self.docs if "/".join(d.file_path.split("/")[:-1]) in old]
            findings.append(Insight(
                type="old_forgotten_folders",
                severity="info",
                title="Old Forgotten Folders",
                description=f"{len(old)} folders have not been updated in over 2 years.",
                affected_pdf_ids=ids[:10],
                extra_data={"folders": old[:5]}
            ))
        return findings

    def research_trends(self) -> List[Insight]:
        # Keywords whose frequency has doubled in last year
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        old_kw = Counter()
        new_kw = Counter()
        for doc in self.docs:
            if not doc.modified_time:
                continue
            for kw in doc.keywords or []:
                if doc.modified_time < one_year_ago:
                    old_kw[kw.lower()] += 1
                else:
                    new_kw[kw.lower()] += 1
        trending = []
        for kw, cnt in new_kw.items():
            if old_kw.get(kw, 0) * 2 < cnt and cnt > 3:
                trending.append(kw)
        if trending:
            ids = [d.id for d in self.docs if any(kw in d.keywords for kw in trending)]
            findings.append(Insight(
                type="research_trends",
                severity="info",
                title="Emerging Research Trends",
                description=f"Keywords showing strong growth: {', '.join(trending[:5])}",
                affected_pdf_ids=ids[:10],
                extra_data={"trending": trending[:10]}
            ))
        return findings