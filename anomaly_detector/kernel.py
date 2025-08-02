from pathlib import Path


def ensure_dir(path: Path):
    """Ensure a directory exists. If path is a file, ensure its parent exists."""
    if path.suffix:  # It's a file
        path = path.parent
    if path and not path.exists():
        path.mkdir(parents=True, exist_ok=True)
