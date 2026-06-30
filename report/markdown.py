"""
Generates clean Markdown summaries detailing scan insights, classification tallies, and integrity flags.
"""

import time
from pathlib import Path
from models.scan_context import ScanReport
from utils.helpers import format_size


class MarkdownReport:
    """Transforms completed pipeline run telemetry into readable Markdown documentation."""

    def generate(self, report_data: ScanReport) -> str:
        """
        Compiles run data into a standardized report structure conforming to Section 11 specifications.
        """
        duration = report_data.end_time - report_data.start_time
        
        lines = [
            f"# 📄 PDF Scan Analytics Execution Report — `{report_data.run_id}`",
            "",
            "## 📊 Run Overview",
            "---",
            f"* **Total PDFs Indexed:** {report_data.total_pdfs}",
            f"* **Total Storage Volume:** {format_size(report_data.total_size_bytes)}",
            f"* **Execution Performance:** {duration:.2f} seconds",
            "",
            "## 📂 Category Summary Breakdown",
            "---",
            "| Category | Occurrences |",
            "| :--- | :--- |"
        ]

        for cat, count in sorted(report_data.global_category_breakdown.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {cat} | {count} |")

        lines.extend([
            "",
            "## 📁 Directory Analysis Summary",
            "---",
            "| Folder Location | Total Files | Size Data | Directory Score |",
            "| :--- | :--- | :--- | :--- |"
        ])

        for path_str, folder in sorted(report_data.folder_summaries.items()):
            lines.append(f"| `{path_str}` | {folder.total_files} | {format_size(folder.total_size_bytes)} | **{folder.folder_score:.1f}** |")

        lines.extend([
            "",
            "## 🔍 Noteworthy Analytical Findings",
            "---"
        ])

        if report_data.findings:
            for issue in report_data.findings:
                lines.append(f"* ⚠️ {issue}")
        else:
            lines.append("* No structural file structure layout issues detected during this scan pass.*")

        lines.append("")
        return "\n".join(lines)