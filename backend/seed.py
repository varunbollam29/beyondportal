"""Idempotent seed data for the Beyond Portal POC: Lucy, sample content, and
signal weight config. Safe to re-run — existing rows (matched by their
natural key) are left untouched rather than duplicated."""

import json
from datetime import datetime

from db import SessionLocal
from models import ContentItem, SignalWeightConfig, User

LUCY_USERNAME = "lucy"

ARTICLES = [
    {
        "title": "2026 Market Outlook: What Client Executives Need to Know",
        "body_text": (
            "Client executives face a shifting market landscape in 2026. "
            "Interest rate normalization, sector rotation, and evolving "
            "client expectations mean the playbook that worked last year "
            "needs a refresh. This article walks through the three market "
            "trends most likely to affect client conversations this quarter "
            "and how to bring them up proactively."
        ),
        "topic_tags": ["markets", "trends"],
    },
    {
        "title": "Leading Through Change: A Playbook for Client Executives",
        "body_text": (
            "Change fatigue is real, and client-facing leaders often absorb "
            "it on behalf of their teams. This piece covers practical "
            "leadership techniques for keeping a team steady during "
            "reorganizations, tool migrations, and shifting client "
            "mandates, with an emphasis on transparent communication."
        ),
        "topic_tags": ["leadership", "management"],
    },
    {
        "title": "Digital Transformation in Client Services",
        "body_text": (
            "Digital transformation is often framed as a technology "
            "project, but for client services teams it is really a "
            "workflow project. This article looks at how AI-assisted "
            "tools are changing day-to-day client servicing, and what "
            "client executives should watch for as their firms adopt them."
        ),
        "topic_tags": ["technology", "digital_transformation"],
    },
    {
        "title": "Building Trust: The Foundation of Client Relationships",
        "body_text": (
            "Trust is built in small moments: a fast response, a proactive "
            "heads-up, an honest answer to a hard question. This article "
            "breaks down the habits that separate client executives who "
            "are seen as trusted advisors from those who are seen as "
            "vendors."
        ),
        "topic_tags": ["client_success", "relationship_management"],
    },
]

VIDEOS = [
    {
        "title": "Inside the Market: Trends Shaping Client Strategy",
        "duration": 480,
        "topic_tags": ["markets", "trends"],
    },
    {
        "title": "Leadership Spotlight: Coaching High-Performing Teams",
        "duration": 360,
        "topic_tags": ["leadership"],
    },
    {
        "title": "The Future of Digital Client Engagement",
        "duration": 420,
        "topic_tags": ["technology", "digital_transformation"],
    },
]

SIGNAL_WEIGHTS = {
    "ARTICLE_READ": 10.0,
    "VIDEO_WATCHED": 15.0,
    "SUMMARIZE_USED": 5.0,
    "SIMPLIFY_USED": 5.0,
    "TRANSLATE_USED": 5.0,
    "ASK_AI_USED": 5.0,
}


def seed_lucy(db) -> None:
    if db.query(User).filter_by(username=LUCY_USERNAME).first():
        return
    db.add(
        User(
            name="Lucy Chen",
            username=LUCY_USERNAME,
            password="lucy123",
            persona="Client Executive",
            declared_interests=json.dumps(
                ["market_trends", "leadership", "digital_transformation"]
            ),
            created_at=datetime.utcnow(),
        )
    )


def seed_content(db) -> None:
    existing_titles = {title for (title,) in db.query(ContentItem.title).all()}

    for article in ARTICLES:
        if article["title"] in existing_titles:
            continue
        db.add(
            ContentItem(
                type="article",
                title=article["title"],
                body_text=article["body_text"],
                topic_tags=json.dumps(article["topic_tags"]),
                published_at=datetime.utcnow(),
            )
        )

    for video in VIDEOS:
        if video["title"] in existing_titles:
            continue
        db.add(
            ContentItem(
                type="video",
                title=video["title"],
                duration=video["duration"],
                topic_tags=json.dumps(video["topic_tags"]),
                published_at=datetime.utcnow(),
            )
        )


def seed_signal_weights(db) -> None:
    existing = {
        signal_type: config
        for signal_type, config in (
            (row.signal_type, row) for row in db.query(SignalWeightConfig).all()
        )
    }
    for signal_type, weight in SIGNAL_WEIGHTS.items():
        if signal_type in existing:
            continue
        db.add(SignalWeightConfig(signal_type=signal_type, weight=weight))


def main() -> None:
    db = SessionLocal()
    try:
        seed_lucy(db)
        seed_content(db)
        seed_signal_weights(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
