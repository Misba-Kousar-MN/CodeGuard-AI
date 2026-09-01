import os
from typing import Tuple, Optional

MAX_FILE_SIZE_BYTES = 256 * 1024  # 256 KB limit for MVP

ALLOWED_EXTENSIONS = {".py", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".java", ".js", ".txt"}

def validate_uploaded_file(file_name: str, file_bytes: bytes) -> Tuple[bool, str]:
    """
    Validates uploaded file size and extension.
    Returns (is_valid, error_message)
    """
    if not file_bytes or len(file_bytes.strip()) == 0:
        return False, "The uploaded file is empty."

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return False, f"File size exceeds limit ({len(file_bytes) // 1024} KB > {MAX_FILE_SIZE_BYTES // 1024} KB)."

    ext = os.path.splitext(file_name)[1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file extension '{ext}'. Supported languages: Python (.py), C++ (.cpp, .h), Java (.java)."

    return True, ""


def read_uploaded_file(file_bytes: bytes) -> Tuple[Optional[str], str]:
    """Reads bytes into UTF-8 string gracefully handling decoding errors."""
    try:
        content = file_bytes.decode("utf-8")
        return content, ""
    except UnicodeDecodeError:
        try:
            content = file_bytes.decode("latin-1")
            return content, ""
        except Exception as e:
            return None, f"Failed to decode file encoding: {e}"
