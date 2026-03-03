"""File discovery module - recursively scans codebase directories."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# File extensions to include
COBOL_EXTENSIONS = {".cob", ".cbl", ".cpy", ".CBL", ".COB"}
C_EXTENSIONS = {".c", ".h"}
CONFIG_EXTENSIONS = {".conf"}
ALL_EXTENSIONS = COBOL_EXTENSIONS | C_EXTENSIONS | CONFIG_EXTENSIONS


@dataclass
class FileInfo:
    """Information about a discovered source file."""
    absolute_path: str
    relative_path: str
    extension: str
    size_bytes: int
    line_count: int = 0
    language: str = ""

    def __post_init__(self):
        ext = self.extension.lower()
        if ext in {".cob", ".cbl", ".cpy"}:
            self.language = "cobol"
        elif ext in {".c", ".h"}:
            self.language = "c"
        elif ext in {".conf"}:
            self.language = "config"
        else:
            self.language = "unknown"


@dataclass
class ScanResult:
    """Result of scanning a codebase directory."""
    files: List[FileInfo] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    languages: dict = field(default_factory=dict)


def count_lines(file_path: str) -> int:
    """Count lines in a file with encoding fallback."""
    encodings = ["utf-8", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return sum(1 for _ in f)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 0


def scan_codebase(
    codebase_path: str,
    extensions: Optional[set] = None,
    exclude_dirs: Optional[set] = None,
) -> ScanResult:
    """
    Recursively scan a codebase directory for source files.

    Args:
        codebase_path: Root directory to scan
        extensions: Set of file extensions to include (default: all supported)
        exclude_dirs: Directory names to skip (default: common build/test dirs)

    Returns:
        ScanResult with all discovered files and statistics
    """
    if extensions is None:
        extensions = ALL_EXTENSIONS
    if exclude_dirs is None:
        exclude_dirs = {".git", "__pycache__", "node_modules", ".svn"}

    root = Path(codebase_path).resolve()
    result = ScanResult()

    if not root.exists():
        raise FileNotFoundError(f"Codebase path not found: {codebase_path}")

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            ext = Path(filename).suffix
            if ext.lower() not in {e.lower() for e in extensions}:
                continue

            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, root)
            size = os.path.getsize(abs_path)
            lines = count_lines(abs_path)

            file_info = FileInfo(
                absolute_path=abs_path,
                relative_path=rel_path,
                extension=ext,
                size_bytes=size,
                line_count=lines,
            )

            result.files.append(file_info)
            result.total_lines += lines
            result.total_bytes += size

            lang = file_info.language
            if lang not in result.languages:
                result.languages[lang] = {"files": 0, "lines": 0}
            result.languages[lang]["files"] += 1
            result.languages[lang]["lines"] += lines

    result.total_files = len(result.files)
    result.files.sort(key=lambda f: f.relative_path)

    return result
