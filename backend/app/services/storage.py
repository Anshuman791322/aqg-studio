"""Storage path construction, sanitization, and security validation services."""

import re
import uuid
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("app.services.storage")
settings = get_settings()

# Characters allowed in sanitized filenames
SAFE_FILENAME_REGEX = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and special character exploits."""
    raw = filename.strip()
    if not raw:
        return "unnamed_document"

    # Normalize backslashes to forward slashes for cross-platform safety
    normalized = raw.replace("\\", "/")
    # Strip any leading/trailing paths
    name = Path(normalized).name
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


def get_storage_base_url() -> str | None:
    """Retrieve Supabase Storage API base endpoint if configured."""
    url = settings.NEXT_PUBLIC_SUPABASE_URL
    if not url:
        return None
    return f"{url.rstrip('/')}/storage/v1"


def get_storage_headers() -> dict[str, str] | None:
    """Retrieve service role authorization headers for storage operations."""
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if not key:
        return None
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }


async def upload_file_to_storage(
    bucket: str,
    path: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> bool:
    """Upload a file payload to Supabase Storage bucket via REST API."""
    base_url = get_storage_base_url()
    headers = get_storage_headers()
    if not base_url or not headers:
        return False

    upload_url = f"{base_url}/object/{bucket}/{path.lstrip('/')}"
    headers["Content-Type"] = content_type
    headers["x-upsert"] = "true"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(upload_url, content=content, headers=headers)
            if resp.status_code in (200, 201):
                return True
            logger.warning(
                f"Storage upload to {bucket}/{path} returned status {resp.status_code}: {resp.text}"
            )
            return False
    except Exception as exc:
        logger.warning(f"Failed to upload {path} to storage bucket {bucket}: {exc}")
        return False


async def download_file_from_storage(bucket: str, path: str) -> bytes | None:
    """Download a file payload from Supabase Storage bucket via REST API."""
    base_url = get_storage_base_url()
    headers = get_storage_headers()
    if not base_url or not headers:
        return None

    download_url = f"{base_url}/object/{bucket}/{path.lstrip('/')}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(download_url, headers=headers)
            if resp.status_code == 200:
                return resp.content
            return None
    except Exception as exc:
        logger.warning(f"Failed to download {path} from storage bucket {bucket}: {exc}")
        return None


async def delete_file_from_storage(bucket: str, path: str) -> bool:
    """Delete a file from Supabase Storage bucket via REST API."""
    base_url = get_storage_base_url()
    headers = get_storage_headers()
    if not base_url or not headers:
        return False

    delete_url = f"{base_url}/object/{bucket}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.request(
                "DELETE",
                delete_url,
                json={"prefixes": [path.lstrip("/")]},
                headers=headers,
            )
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.warning(f"Failed to delete {path} from storage bucket {bucket}: {exc}")
        return False


async def create_signed_download_url(
    bucket: str, path: str, expires_in_seconds: int = 3600
) -> str | None:
    """Generate a short-lived signed download URL for private storage assets."""
    base_url = get_storage_base_url()
    headers = get_storage_headers()
    if not base_url or not headers:
        return None

    sign_url = f"{base_url}/object/sign/{bucket}/{path.lstrip('/')}"
    headers["Content-Type"] = "application/json"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                sign_url,
                json={"expiresIn": expires_in_seconds},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                signed_url_path = data.get("signedURL")
                if signed_url_path:
                    # Return full signed URL
                    return f"{base_url}{signed_url_path}"
            return None
    except Exception as exc:
        logger.warning(f"Failed to generate signed URL for {path} in bucket {bucket}: {exc}")
        return None
