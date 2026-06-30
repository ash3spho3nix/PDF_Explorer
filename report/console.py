"""
Handles rendering terminal interfaces, progress metrics, and summary data blocks via Rich.
"""

from rich.console import Console
from rich.table import Table
from models.scan_context import ScanReport
from utils.helpers import format_size

console = Console()


class ConsoleReport:
    """Renders highly scannable command-line visual data blocks directly into interactive shells."""

    def display_summary(self, report_data: ScanReport):
        """Prints a highly polished terminal readout summarizing execution data."""
        console.print("\n[bold green]🏁 Scan Pipeline Execution Completed Successfully![/bold green]\n")
        
        table = Table(title="PDF Inventory High-Level Metadata Summary", title_style="bold magenta")
        table.add_column("Metric Name", style="cyan")
        table.add_column("Accumulated Measurement", style="white")

        table.add_row("Run Identifier", report_data.run_id)
        table.add_row("Total Documents Found", str(report_data.total_pdfs))
        table.add_row("Total Size Monitored", format_size(report_data.total_size_bytes))
        table.add_row("Duration Context", f"{(report_data.end_time - report_data.start_time):.2f} seconds")

        console.print(table)