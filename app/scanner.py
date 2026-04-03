from __future__ import annotations

from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


def scan_video_files(directory: str) -> list[Path]:
    root = Path(directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory not found: {root}")

    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            files.append(path)
    return files
