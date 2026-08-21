"""One-off, idempotent helper for swapping placeholder content_items rows
for real content as Neha provides it. Plain UPDATE by content_id — no new
rows, no ID generation needed, since the real rows already exist.

Usage: update_content_item(db, "v001", title=..., blob_url=..., ...) then
commit. Only pass the fields that actually changed; omitted fields are
left untouched.
"""

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import ContentItem

# Seconds between the MP4/QuickTime epoch (1904-01-01) and Unix epoch (1970-01-01).
_MP4_EPOCH_OFFSET = 2082844800

_UPDATABLE_FIELDS = {
    "title", "body_text", "blob_url", "thumbnail_url", "duration", "topic_tags",
    "published_at",
}


def update_content_item(db: Session, content_id: str, **fields: Any) -> ContentItem:
    item = db.get(ContentItem, content_id)
    if item is None:
        raise ValueError(f"content_id {content_id} does not exist")

    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Not updatable field(s): {sorted(unknown)}")

    if "topic_tags" in fields and isinstance(fields["topic_tags"], list):
        fields["topic_tags"] = json.dumps(fields["topic_tags"])

    for name, value in fields.items():
        setattr(item, name, value)

    return item


def _read_mvhd(data: bytes) -> bytes:
    """Return the raw content bytes of the top-level moov/mvhd box — no
    ffprobe/FFmpeg needed, stdlib binary parsing only. Shared by
    get_mp4_duration() and get_mp4_creation_date()."""

    def read_box(pos: int) -> tuple[str, int, int]:
        size = int.from_bytes(data[pos:pos + 4], "big")
        box_type = data[pos + 4:pos + 8].decode("ascii", errors="ignore")
        header_size = 8
        if size == 1:
            size = int.from_bytes(data[pos + 8:pos + 16], "big")
            header_size = 16
        elif size == 0:
            size = len(data) - pos
        return box_type, pos + header_size, pos + size

    pos, moov_start, moov_end = 0, None, None
    while pos < len(data) - 8:
        box_type, content_start, box_end = read_box(pos)
        if box_type == "moov":
            moov_start, moov_end = content_start, box_end
            break
        pos = box_end
    if moov_start is None:
        raise ValueError("No 'moov' box found — is this a valid MP4 file?")

    pos = moov_start
    while pos < moov_end - 8:
        box_type, content_start, box_end = read_box(pos)
        if box_type == "mvhd":
            return data[content_start:box_end]
        pos = box_end
    raise ValueError("No 'mvhd' box found inside 'moov' — is this a valid MP4 file?")


def get_mp4_duration(data: bytes) -> str:
    """Returns "m:ss" to match the existing duration format (e.g. "6:32")."""
    mvhd = _read_mvhd(data)
    version = mvhd[0]
    if version == 1:
        timescale = int.from_bytes(mvhd[20:24], "big")
        duration = int.from_bytes(mvhd[24:32], "big")
    else:
        timescale = int.from_bytes(mvhd[12:16], "big")
        duration = int.from_bytes(mvhd[16:20], "big")
    total_seconds = round(duration / timescale)
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def get_mp4_creation_date(data: bytes) -> date | None:
    """Returns the MP4's embedded creation date, or None if the encoder
    never set it — very common; many export/upload tools leave this
    field at 0, in which case the caller should fall back to a flagged
    placeholder rather than trust a bogus 1904 epoch date."""
    mvhd = _read_mvhd(data)
    version = mvhd[0]
    creation_time = int.from_bytes(mvhd[4:12] if version == 1 else mvhd[4:8], "big")
    if creation_time == 0:
        return None
    return datetime.fromtimestamp(creation_time - _MP4_EPOCH_OFFSET, tz=timezone.utc).date()
