"""
Manages rendering active multi-tier task monitoring status blocks using Rich environments.
"""

from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn


def create_pipeline_progress() -> Progress:
    """
    Builds an isolated multi-stage rendering progress interface context for active execution tracks.
    """
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn()
    )