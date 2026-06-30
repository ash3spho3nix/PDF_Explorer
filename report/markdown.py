"""
Generates clean Markdown summaries detailing scan insights, classification tallies, and integrity flags.
"""

import time
from pathlib import Path
from models.scan_context import ScanReport, FolderSummary
from utils.helpers import format_size


class MarkdownReport:
    """Transforms completed pipeline run telemetry into readable Markdown documentation."""

    def generate(self, report_data: ScanReport) -> str:
        """
        Compiles run data into a standardized report structure conforming to Section 11 specifications.
        """
        # Support being passed either a full ScanReport or a lightweight ScanResult
        if not hasattr(report_data, "run_id"):
            # Build compatible view from ScanResult
            run_id = getattr(report_data, "root_path", "") or ""
            start_time = getattr(report_data, "start_time", 0)
            end_time = getattr(report_data, "end_time", 0)
            total_pdfs = getattr(report_data, "total_files", len(getattr(report_data, "pdfs", [])))
            total_size_bytes = sum(p.size_bytes for p in getattr(report_data, "pdfs", []))
            # category breakdown from stats or compute
            stats = getattr(report_data, "stats", {}) or {}
            category_breakdown = {k: v.get("count", 0) for k, v in stats.get("category_breakdown", {}).items()} if stats.get("category_breakdown") else {}
            if not category_breakdown:
                for p in getattr(report_data, "pdfs", []):
                    category_breakdown[p.category] = category_breakdown.get(p.category, 0) + 1
            # folder summaries: use folder_summaries if present, else build basic summaries
            folder_summaries = {}
            if hasattr(report_data, "folder_summaries") and report_data.folder_summaries:
                folder_summaries = report_data.folder_summaries
            else:
                # Build simple FolderSummary objects
                pdfs_by_folder = {}
                for p in getattr(report_data, "pdfs", []):
                    pdfs_by_folder.setdefault(p.parent_folder, []).append(p)
                for folder, pdfs in pdfs_by_folder.items():
                    category_counts = {}
                    for x in pdfs:
                        category_counts[x.category] = category_counts.get(x.category, 0) + 1
                    folder_summaries[folder] = FolderSummary(
                        folder_path=folder,
                        total_files=len(pdfs),
                        total_size_bytes=sum(x.size_bytes for x in pdfs),
                        category_counts=category_counts,
                        folder_score=0.0
                    )
            findings_list = []
            if getattr(report_data, "findings", None):
                # findings may be list of dicts or strings
                for f in report_data.findings:
                    if isinstance(f, str):
                        findings_list.append(f)
                    elif isinstance(f, dict):
                        findings_list.append(f.get("title", "Finding") + " — " + f.get("description", ""))
            duration = end_time - start_time
            # normalize names used below
            report_ctx = {
                "run_id": run_id,
                "total_pdfs": total_pdfs,
                "total_size_bytes": total_size_bytes,
                "global_category_breakdown": category_breakdown,
                "folder_summaries": folder_summaries,
                "findings": findings_list,
                "start_time": start_time,
                "end_time": end_time,
            }
        else:
            duration = report_data.end_time - report_data.start_time
            report_ctx = report_data

        lines = [
            f"# 📄 PDF Scan Analytics Execution Report — `{report_ctx['run_id'] if isinstance(report_ctx, dict) else report_ctx.run_id}`",
            "",
            "## 📊 Run Overview",
            "---",
            f"* **Total PDFs Indexed:** {report_ctx['total_pdfs'] if isinstance(report_ctx, dict) else report_ctx.total_pdfs}",
            f"* **Total Storage Volume:** {format_size(report_ctx['total_size_bytes'] if isinstance(report_ctx, dict) else report_ctx.total_size_bytes)}",
            f"* **Execution Performance:** {duration:.2f} seconds",
            "",
            "## 📂 Category Summary Breakdown",
            "---",
            "| Category | Occurrences |",
            "| :--- | :--- |"
        ]

        for cat, count in sorted((report_ctx['global_category_breakdown'] if isinstance(report_ctx, dict) else report_ctx.global_category_breakdown).items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {cat} | {count} |")

        lines.extend([
            "",
            "## 📁 Directory Analysis Summary",
            "---",
            "| Folder Location | Total Files | Size Data | Directory Score |",
            "| :--- | :--- | :--- | :--- |"
        ])

        folder_summaries = report_ctx['folder_summaries'] if isinstance(report_ctx, dict) else report_data.folder_summaries
        for path_str, folder in sorted(folder_summaries.items()):
            lines.append(f"| `{path_str}` | {folder.total_files} | {format_size(folder.total_size_bytes)} | **{folder.folder_score:.1f}** |")

        lines.extend([
            "",
            "## 🔍 Noteworthy Analytical Findings",
            "---"
        ])

        findings = report_ctx['findings'] if isinstance(report_ctx, dict) else report_data.findings
        if findings:
            for issue in findings:
                lines.append(f"* ⚠️ {issue}")
        else:
            lines.append("* No structural file structure layout issues detected during this scan pass.*")

        lines.append("")
        return "\n".join(lines)