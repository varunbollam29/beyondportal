"""Shared Azure Blob Storage client for the two POC containers (articles,
videos). See CLAUDE.md Section 2/8 task 2.2."""

import urllib.parse

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobServiceClient, ContentSettings

from config import settings

_service_client = BlobServiceClient.from_connection_string(
    settings.storage_connection_string
)


def upload_file(container: str, blob_name: str, data: bytes, content_type: str | None = None) -> str:
    """Upload bytes to the given container, overwriting any existing blob
    with the same name, and return the resulting blob URL."""
    content_settings = ContentSettings(content_type=content_type) if content_type else None
    try:
        blob_client = _service_client.get_blob_client(container=container, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
    except AzureError as exc:
        raise RuntimeError(f"Failed to upload blob '{blob_name}' to container '{container}'") from exc
    return blob_client.url


def get_blob_url(container: str, blob_name: str) -> str:
    """Return the URL for a blob without checking whether it exists."""
    return _service_client.get_blob_client(container=container, blob=blob_name).url


def download_blob_from_url(blob_url: str) -> bytes:
    """Download blob bytes given the full URL stored in
    content_items.blob_url, reusing the same authenticated client as
    upload_file/get_blob_url."""
    path = urllib.parse.unquote(urllib.parse.urlparse(blob_url).path)
    container, blob_name = path.lstrip("/").split("/", 1)
    try:
        return _service_client.get_blob_client(container=container, blob=blob_name).download_blob().readall()
    except AzureError as exc:
        raise RuntimeError(f"Failed to download blob from '{blob_url}'") from exc
