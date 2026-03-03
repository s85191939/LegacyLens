"""Preprocessing module - handles encoding, normalization, and COBOL formatting."""

from typing import Optional, Tuple


def read_file_safe(file_path: str) -> Tuple[str, str]:
    """
    Read a file with encoding detection fallback.

    Returns:
        Tuple of (content, encoding_used)
    """
    encodings = ["utf-8", "latin-1", "cp1252", "ascii"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Last resort: read as bytes and decode with replacement
    with open(file_path, "rb") as f:
        content = f.read().decode("utf-8", errors="replace")
    return content, "utf-8-replace"


def normalize_content(content: str) -> str:
    """Normalize line endings and trailing whitespace."""
    # Normalize line endings to \n
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    # Remove trailing whitespace per line
    lines = [line.rstrip() for line in content.split("\n")]
    return "\n".join(lines)


def is_cobol_fixed_format(content: str) -> bool:
    """
    Detect if COBOL source uses fixed-format (columns matter).
    Fixed format: cols 1-6 sequence, col 7 indicator, cols 8-72 code, cols 73-80 ID.
    """
    lines = content.split("\n")
    fixed_indicators = 0
    total_lines = 0

    for line in lines[:50]:  # Check first 50 lines
        if len(line) < 7:
            continue
        total_lines += 1
        col7 = line[6] if len(line) > 6 else " "
        # In fixed format, column 7 is often space, *, or -
        if col7 in (" ", "*", "-", "/", "D", "d"):
            fixed_indicators += 1

    if total_lines == 0:
        return True  # Default to fixed
    return (fixed_indicators / total_lines) > 0.7


def extract_cobol_code(line: str, is_fixed: bool) -> str:
    """
    Extract the code portion from a COBOL line.
    In fixed format, code is in columns 8-72.
    """
    if not is_fixed:
        return line
    if len(line) < 8:
        return ""
    # Column 7 is indicator
    indicator = line[6] if len(line) > 6 else " "
    if indicator == "*" or indicator == "/":
        # Comment line - keep it with a marker
        return f"*> COMMENT: {line[7:72].rstrip()}"
    if indicator == "-":
        # Continuation line
        return line[7:72].rstrip()
    # Normal code line (columns 8-72)
    return line[7:72].rstrip()


def preprocess_file(file_path: str) -> Tuple[str, dict]:
    """
    Preprocess a source file for chunking.

    Returns:
        Tuple of (processed_content, metadata)
    """
    content, encoding = read_file_safe(file_path)
    content = normalize_content(content)

    metadata = {
        "encoding": encoding,
        "original_lines": len(content.split("\n")),
    }

    ext = file_path.lower().split(".")[-1]
    if ext in ("cob", "cbl", "cpy"):
        is_fixed = is_cobol_fixed_format(content)
        metadata["format"] = "fixed" if is_fixed else "free"
        # Keep original content with line numbers for reference
        # but also note the format for the chunker
        metadata["is_cobol"] = True
        metadata["is_fixed_format"] = is_fixed
    else:
        metadata["is_cobol"] = False
        metadata["is_fixed_format"] = False

    return content, metadata
