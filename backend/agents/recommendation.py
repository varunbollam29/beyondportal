"""Content Recommendation Agent (#3) — see CLAUDE.md Section 6. Tag-overlap
scoring only, no ML, no vector search.

'Upsert' here means: expire this user's previous ACTIVE recommendation rows
and insert a fresh ACTIVE set — the schema has no unique constraint to
upsert against, and status already models exactly this ACTIVE/EXPIRED
lifecycle.
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from constants import INTEREST_TO_TAG
from db import next_id
from models import ContentItem, EngagementSignal, Recommendation, User

_TOP_N = 5
_CONSUMED_SIGNAL_TYPES = ("ARTICLE_READ", "VIDEO_WATCHED")


def _interest_tags(declared_interests: list[str]) -> set[str]:
    tags: set[str] = set()
    for interest in declared_interests:
        tags.update(INTEREST_TO_TAG.get(interest, []))
    return tags


def get_recommendations(db: Session, user_id: str) -> list[dict[str, Any]]:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"user_id {user_id} does not exist")

    interest_tags = _interest_tags(json.loads(user.declared_interests))

    consumed_content_ids = {
        row.content_id
        for row in db.execute(
            select(EngagementSignal.content_id).where(
                EngagementSignal.user_id == user_id,
                EngagementSignal.signal_type.in_(_CONSUMED_SIGNAL_TYPES),
            )
        )
    }

    candidates_query = select(ContentItem)
    if consumed_content_ids:
        candidates_query = candidates_query.where(
            ContentItem.content_id.notin_(consumed_content_ids)
        )
    candidates = db.execute(candidates_query).scalars().all()

    scored: list[tuple[ContentItem, float, list[str]]] = []
    for item in candidates:
        item_tags = json.loads(item.topic_tags)
        if not item_tags:
            continue
        matched = [tag for tag in item_tags if tag in interest_tags]
        if not matched:
            continue
        score = min(1.0, len(matched) / len(item_tags))
        scored.append((item, score, matched))

    scored.sort(key=lambda row: row[1], reverse=True)
    top = scored[:_TOP_N]

    if not top:
        top = [
            (item, 0.0, [])
            for item in sorted(candidates, key=lambda c: c.published_at, reverse=True)[:_TOP_N]
        ]

    db.execute(
        update(Recommendation)
        .where(Recommendation.user_id == user_id, Recommendation.status == "ACTIVE")
        .values(status="EXPIRED")
    )

    now = datetime.utcnow()
    results = []
    for rank, (item, score, matched) in enumerate(top, start=1):
        reason_code = (
            f"Matches your interest: {matched[0]}" if matched else "Recently published"
        )
        db.add(
            Recommendation(
                rec_id=next_id(db, Recommendation.rec_id, "r"),
                user_id=user_id,
                content_id=item.content_id,
                rank=rank,
                score=score,
                reason_code=reason_code,
                status="ACTIVE",
                generated_at=now,
            )
        )
        db.flush()  # so the next loop iteration's next_id() sees this row
        results.append(
            {
                "content_id": item.content_id,
                "rank": rank,
                "score": score,
                "reason_code": reason_code,
            }
        )

    db.commit()
    return results
