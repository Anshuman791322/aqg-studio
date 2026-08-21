"""Storage path construction, sanitization, and security validation services."""

import re
import uuid
from pathlib import Path

# Characters allowed in sanitized filenames
SAFE_FILENAME_REGEX = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and special character exploits."""
    raw = filename.strip()
    if not raw:
        return "unnamed_document"

    # Strip any leading/trailing paths
    name = Path(raw).name
    # Replace unsafe characters with underscore
    sanitized = SAFE_FILENAME_REGEX.sub("_", name)
    # Strip leading dots and underscores to avoid hidden/empty files
    cleaned = sanitized.strip("._ ")
    if not cleaned:
        return "unnamed_document"
    return cleaned[:255]


def build_document_storage_path(
    user_id: uuid.UUID, document_id: uuid.UUID, filename: str
) -> str:
    """Construct deterministic private storage path for user uploaded document."""
    safe_name = sanitize_filename(filename)
    return f"{user_id}/{document_id}/{safe_name}"


def build_export_storage_path(
    user_id: uuid.UUID,
    assessment_id: uuid.UUID,
    export_id: uuid.UUID,
    extension: str,
) -> str:
    """Construct deterministic private storage path for generated assessment export."""
    ext = extension.lstrip(".").lower()
    return f"{user_id}/{assessment_id}/{export_id}.{ext}"


def validate_storage_path(path: str, user_id: uuid.UUID) -> bool:
    """Validate that storage path belongs strictly to the authenticated user."""
    if not path or ".." in path or "\\" in path or "\x00" in path:
        return False

    segments = [s.strip() for s in path.split("/") if s.strip()]
    if len(segments) < 2:
        return False

    # Verify first segment is a valid UUID matching user_id (case-insensitive)
    try:
        path_user_id = uuid.UUID(segments[0])
        return path_user_id == user_id
    except ValueError:
        return False
