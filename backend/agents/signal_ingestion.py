"""Signal Ingestion Agent (#1) and Engagement Scoring Agent (#2) — see
CLAUDE.md Section 6. Scoring is kept in this module per Section 8 task 3.1,
since it's only ever invoked from signal ingestion, not its own route.

ValueError means bad caller input (400 territory) — main.py's route (task
4.1) should map it accordingly instead of leaking a raw traceback. A
Scoring Agent failure does NOT roll back the signal write: the raw signal
is durable proof the interaction happened even if scoring couldn't run.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from constants import SIGNAL_TYPES
from db import next_id
from models import ContentItem, EngagementScore, EngagementSignal, SignalWeightConfig, User

logger = logging.getLogger(__name__)

_LEVEL_THRESHOLDS = (
    (40.0, "Getting Started"),
    (75.0, "Active"),
)


def _level_for_score(score: float) -> str:
    for threshold, level in _LEVEL_THRESHOLDS:
        if score < threshold:
            return level
    return "Very Active"


def update_engagement_score(
    db: Session, user_id: str, signal_type: str, depth_pct: float | None
) -> EngagementScore:
    """Engagement Scoring Agent (#2). A missing weight config row is not
    an error — it just contributes zero to the score."""
    weight_config = db.get(SignalWeightConfig, signal_type)
    if weight_config is None:
        logger.warning("No weight configured for signal_type '%s'; using 0", signal_type)
        weight = 0.0
    else:
        weight = weight_config.weight

    delta = weight * (depth_pct / 100) if depth_pct is not None else weight

    score_row = db.get(EngagementScore, user_id)
    current_score = score_row.score if score_row else 0.0

    new_score = round(min(100.0, current_score + delta))
    now = datetime.utcnow()

    if score_row is None:
        score_row = EngagementScore(
            user_id=user_id,
            score=new_score,
            level=_level_for_score(new_score),
            delta=delta,
            last_updated=now,
        )
        db.add(score_row)
    else:
        score_row.score = new_score
        score_row.level = _level_for_score(new_score)
        score_row.delta = delta
        score_row.last_updated = now

    db.commit()
    return score_row


def log_signal(
    db: Session,
    user_id: str,
    content_id: str,
    signal_type: str,
    depth_pct: float | None = None,
) -> dict[str, Any]:
    """Signal Ingestion Agent (#1). Validates input, writes the raw signal
    (no dedup — every signal is logged, even repeats), then triggers the
    Scoring Agent. Returns the response shape the /signals route will pass
    straight through to the client."""
    if signal_type not in SIGNAL_TYPES:
        raise ValueError(f"Unknown signal_type '{signal_type}'")
    if depth_pct is not None and not 0 <= depth_pct <= 100:
        raise ValueError("depth_pct must be between 0 and 100")
    if db.get(User, user_id) is None:
        raise ValueError(f"user_id {user_id} does not exist")
    if db.get(ContentItem, content_id) is None:
        raise ValueError(f"content_id {content_id} does not exist")

    signal = EngagementSignal(
        signal_id=next_id(db, EngagementSignal.signal_id, "s"),
        user_id=user_id,
        content_id=content_id,
        signal_type=signal_type,
        depth_pct=depth_pct,
        occurred_at=datetime.utcnow(),
    )
    db.add(signal)
    db.commit()

    try:
        score_row = update_engagement_score(db, user_id, signal_type, depth_pct)
    except Exception:
        logger.exception("Scoring Agent failed for user_id %s", user_id)
        return {"signal_id": signal.signal_id, "score_updated": False}

    return {
        "signal_id": signal.signal_id,
        "score_updated": True,
        "new_score": score_row.score,
        "delta": score_row.delta,
    }
