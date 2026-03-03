"""
Syntax-aware code chunker for COBOL, C, and generic files.

Chunking strategies:
1. COBOL: DIVISION → SECTION → PARAGRAPH boundaries
2. C: Function-level splitting
3. Fallback: Fixed-size with overlap (token-based)
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional

import tiktoken


@dataclass
class CodeChunk:
    """A chunk of source code with metadata."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str  # "division", "section", "paragraph", "function", "fixed"
    name: str = ""
    division: str = ""
    section: str = ""
    language: str = ""
    dependencies: List[str] = field(default_factory=list)
    tokens: int = 0
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()


# Token encoder
_encoder = None


def get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    return len(get_encoder().encode(text))


# ---------- COBOL Chunking ----------

# COBOL division pattern
DIVISION_PATTERN = re.compile(
    r"^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION",
    re.IGNORECASE | re.MULTILINE,
)

# COBOL section pattern
SECTION_PATTERN = re.compile(
    r"^\s*([A-Z][A-Z0-9\-]*)\s+SECTION\s*\.",
    re.IGNORECASE | re.MULTILINE,
)

# COBOL paragraph pattern (name at start of line, followed by period on same/next line)
PARAGRAPH_PATTERN = re.compile(
    r"^(\s{0,3}[A-Z][A-Z0-9\-]*)\s*\.\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# COBOL dependency patterns
PERFORM_PATTERN = re.compile(r"PERFORM\s+([A-Z][A-Z0-9\-]*)", re.IGNORECASE)
CALL_PATTERN = re.compile(r"CALL\s+['\"]([^'\"]+)['\"]", re.IGNORECASE)
COPY_PATTERN = re.compile(r"COPY\s+([A-Z][A-Z0-9\-]*)", re.IGNORECASE)


def extract_cobol_dependencies(content: str) -> List[str]:
    """Extract dependency references from COBOL code."""
    deps = []
    for m in PERFORM_PATTERN.finditer(content):
        deps.append(f"PERFORM {m.group(1)}")
    for m in CALL_PATTERN.finditer(content):
        deps.append(f"CALL {m.group(1)}")
    for m in COPY_PATTERN.finditer(content):
        deps.append(f"COPY {m.group(1)}")
    return list(set(deps))


def chunk_cobol(content: str, file_path: str) -> List[CodeChunk]:
    """
    Chunk COBOL source code by DIVISION/SECTION/PARAGRAPH boundaries.
    Falls back to fixed-size for very large sections.
    """
    lines = content.split("\n")
    chunks = []

    # Find all structural boundaries
    boundaries = []
    current_division = ""
    current_section = ""

    for i, line in enumerate(lines):
        # Check for division
        div_match = DIVISION_PATTERN.match(line)
        if div_match:
            current_division = div_match.group(1).upper()
            boundaries.append({
                "line": i,
                "type": "division",
                "name": current_division + " DIVISION",
                "division": current_division,
                "section": "",
            })
            continue

        # Check for section
        sec_match = SECTION_PATTERN.match(line)
        if sec_match:
            current_section = sec_match.group(1).upper()
            boundaries.append({
                "line": i,
                "type": "section",
                "name": current_section + " SECTION",
                "division": current_division,
                "section": current_section,
            })
            continue

        # Check for paragraph (only in PROCEDURE DIVISION)
        if current_division == "PROCEDURE":
            para_match = PARAGRAPH_PATTERN.match(line)
            if para_match:
                para_name = para_match.group(1).strip().upper()
                # Skip if it looks like a COBOL keyword
                skip_words = {"IF", "ELSE", "END", "MOVE", "PERFORM", "CALL",
                            "DISPLAY", "ACCEPT", "READ", "WRITE", "STOP", "GO",
                            "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "COMPUTE"}
                if para_name not in skip_words:
                    boundaries.append({
                        "line": i,
                        "type": "paragraph",
                        "name": para_name,
                        "division": current_division,
                        "section": current_section,
                    })

    if not boundaries:
        # No structural elements found - use fixed-size fallback
        return chunk_fixed_size(content, file_path, language="cobol")

    # Create chunks from boundaries
    for idx, boundary in enumerate(boundaries):
        start_line = boundary["line"]
        end_line = boundaries[idx + 1]["line"] - 1 if idx + 1 < len(boundaries) else len(lines) - 1

        chunk_content = "\n".join(lines[start_line:end_line + 1])
        if not chunk_content.strip():
            continue

        tokens = count_tokens(chunk_content)

        # If chunk is too large, split it with fixed-size
        if tokens > 1200:
            sub_chunks = chunk_fixed_size(
                chunk_content, file_path,
                language="cobol",
                start_line_offset=start_line,
                division=boundary["division"],
                section=boundary.get("section", ""),
                parent_name=boundary["name"],
            )
            chunks.extend(sub_chunks)
        else:
            deps = extract_cobol_dependencies(chunk_content)
            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start_line + 1,  # 1-indexed
                end_line=end_line + 1,
                chunk_type=boundary["type"],
                name=boundary["name"],
                division=boundary["division"],
                section=boundary.get("section", ""),
                language="cobol",
                dependencies=deps,
                tokens=tokens,
            )
            chunks.append(chunk)

    return chunks


# ---------- C Chunking ----------

# C function signature patterns (handles brace on same or next line)
C_FUNC_SIGNATURE = re.compile(
    r"^(?:static\s+|extern\s+|inline\s+|const\s+)*"
    r"(?:(?:unsigned|signed|long|short|volatile|struct|enum|union)\s+)*"
    r"(?:void|int|char|float|double|size_t|ssize_t|cob_\w+|cb_\w+|FILE|COB_\w+|\w+_t)\s*\*?\s+"
    r"(\w+)\s*\(",
    re.MULTILINE,
)


def _find_c_functions(lines):
    """Find function start positions in C code using heuristic detection."""
    functions = []  # list of (start_line, name)

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip preprocessor, comments, declarations ending in ;
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        if stripped.endswith(";"):
            continue

        match = C_FUNC_SIGNATURE.match(stripped)
        if match:
            func_name = match.group(1)
            # Check if opening brace is on this line or next few lines
            has_brace = False
            for j in range(i, min(i + 3, len(lines))):
                if "{" in lines[j]:
                    has_brace = True
                    break
            if has_brace:
                functions.append((i, func_name))

    return functions


def chunk_c(content: str, file_path: str) -> List[CodeChunk]:
    """
    Chunk C source code by function definitions.
    Uses brace-depth tracking to find function boundaries.
    Falls back to fixed-size for non-function content.
    """
    lines = content.split("\n")
    functions = _find_c_functions(lines)

    if not functions:
        return chunk_fixed_size(content, file_path, language="c")

    chunks = []
    prev_end = 0

    for idx, (func_start, func_name) in enumerate(functions):
        # Add pre-function content (headers, globals, etc.)
        if func_start > prev_end:
            pre_content = "\n".join(lines[prev_end:func_start])
            if pre_content.strip() and count_tokens(pre_content) >= 20:
                sub_chunks = chunk_fixed_size(
                    pre_content, file_path, language="c",
                    start_line_offset=prev_end,
                    parent_name="(declarations)",
                )
                chunks.extend(sub_chunks)

        # Find function end by tracking brace depth
        brace_depth = 0
        func_end = func_start
        found_open = False

        for j in range(func_start, len(lines)):
            brace_depth += lines[j].count("{") - lines[j].count("}")
            if "{" in lines[j]:
                found_open = True
            if found_open and brace_depth == 0:
                func_end = j
                break
        else:
            func_end = len(lines) - 1

        func_content = "\n".join(lines[func_start:func_end + 1])
        tokens = count_tokens(func_content)

        if tokens > 1200:
            sub_chunks = chunk_fixed_size(
                func_content, file_path, language="c",
                start_line_offset=func_start,
                parent_name=func_name,
            )
            chunks.extend(sub_chunks)
        elif tokens >= 10:
            chunk = CodeChunk(
                content=func_content,
                file_path=file_path,
                start_line=func_start + 1,
                end_line=func_end + 1,
                chunk_type="function",
                name=func_name,
                language="c",
                tokens=tokens,
            )
            chunks.append(chunk)

        prev_end = func_end + 1

    # Handle trailing content
    if prev_end < len(lines):
        tail_content = "\n".join(lines[prev_end:])
        if tail_content.strip() and count_tokens(tail_content) >= 20:
            sub_chunks = chunk_fixed_size(
                tail_content, file_path, language="c",
                start_line_offset=prev_end,
            )
            chunks.extend(sub_chunks)

    if not chunks:
        return chunk_fixed_size(content, file_path, language="c")

    return chunks


# ---------- Fixed-Size Fallback ----------

def chunk_fixed_size(
    content: str,
    file_path: str,
    language: str = "unknown",
    chunk_size: int = 800,
    overlap: int = 150,
    start_line_offset: int = 0,
    division: str = "",
    section: str = "",
    parent_name: str = "",
) -> List[CodeChunk]:
    """
    Fixed-size chunking with token-based overlap.
    Used as fallback when syntax-aware chunking can't find boundaries.
    """
    encoder = get_encoder()
    lines = content.split("\n")
    chunks = []

    current_lines = []
    current_tokens = 0
    chunk_start = 0

    for i, line in enumerate(lines):
        line_tokens = len(encoder.encode(line + "\n"))

        if current_tokens + line_tokens > chunk_size and current_lines:
            # Create chunk
            chunk_content = "\n".join(current_lines)
            deps = extract_cobol_dependencies(chunk_content) if language == "cobol" else []

            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=chunk_start + start_line_offset + 1,
                end_line=chunk_start + len(current_lines) + start_line_offset,
                chunk_type="fixed",
                name=parent_name,
                division=division,
                section=section,
                language=language,
                dependencies=deps,
                tokens=current_tokens,
            )
            chunks.append(chunk)

            # Calculate overlap in lines
            overlap_lines = []
            overlap_tokens = 0
            for prev_line in reversed(current_lines):
                lt = len(encoder.encode(prev_line + "\n"))
                if overlap_tokens + lt > overlap:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_tokens += lt

            chunk_start = i - len(overlap_lines)
            current_lines = overlap_lines
            current_tokens = overlap_tokens

        current_lines.append(line)
        current_tokens += line_tokens

    # Don't forget the last chunk
    if current_lines:
        chunk_content = "\n".join(current_lines)
        deps = extract_cobol_dependencies(chunk_content) if language == "cobol" else []

        chunk = CodeChunk(
            content=chunk_content,
            file_path=file_path,
            start_line=chunk_start + start_line_offset + 1,
            end_line=chunk_start + len(current_lines) + start_line_offset,
            chunk_type="fixed",
            name=parent_name,
            division=division,
            section=section,
            language=language,
            dependencies=deps,
            tokens=count_tokens(chunk_content),
        )
        chunks.append(chunk)

    return chunks


# ---------- Main Entry Point ----------

def chunk_file(content: str, file_path: str, language: str) -> List[CodeChunk]:
    """
    Chunk a file using the appropriate strategy based on language.

    Args:
        content: File content
        file_path: Relative file path
        language: "cobol", "c", or "config"

    Returns:
        List of CodeChunk objects
    """
    if not content.strip():
        return []

    if language == "cobol":
        chunks = chunk_cobol(content, file_path)
    elif language == "c":
        chunks = chunk_c(content, file_path)
    else:
        chunks = chunk_fixed_size(content, file_path, language=language)

    # Filter out empty or very small chunks
    chunks = [c for c in chunks if c.tokens >= 10]

    return chunks
