"""Unit tests for the Content Recommendation Agent (#3) tag-overlap
scoring — see CLAUDE.md Section 11.2: this is the other of the two pieces
of real business logic that must be tested."""

import datetime
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.recommendation import get_recommendations
from models import Base, ContentItem, EngagementSignal, User


class TestRecommendation(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.now = datetime.datetime.utcnow()
        self.today = self.now.date()

    def tearDown(self):
        self.db.close()

    def _add_user(self, user_id, interests):
        self.db.add(
            User(
                user_id=user_id,
                name="U",
                username=f"user-{user_id}",
                password="x",
                persona="Client Executive",
                declared_interests=json.dumps(interests),
                created_at=self.now,
            )
        )

    def _add_content(self, content_id, tags, published_at=None):
        self.db.add(
            ContentItem(
                content_id=content_id,
                type="article",
                title=f"Item {content_id}",
                body_text="body",
                topic_tags=json.dumps(tags),
                published_at=published_at or self.today,
            )
        )

    def test_matching_interest_scores_highest(self):
        self._add_user("u001", ["International Tax"])  # -> INTL_TAX, PILLAR_TWO
        self._add_content("c001", ["INTL_TAX", "PILLAR_TWO"])  # full overlap: score 1.0
        self._add_content("c002", ["INTL_TAX", "unrelated"])  # partial: score 0.5
        self._add_content("c003", ["unrelated"])  # no match: excluded
        self.db.commit()

        recs = get_recommendations(self.db, "u001")
        self.assertEqual([r["content_id"] for r in recs], ["c001", "c002"])
        self.assertEqual(recs[0]["score"], 1.0)
        self.assertEqual(recs[1]["score"], 0.5)

    def test_excludes_already_consumed_content(self):
        self._add_user("u001", ["International Tax"])
        self._add_content("c001", ["INTL_TAX"])
        self._add_content("c002", ["INTL_TAX"])
        self.db.add(
            EngagementSignal(
                signal_id="s001", user_id="u001", content_id="c001",
                signal_type="ARTICLE_READ", depth_pct=90, occurred_at=self.now,
            )
        )
        self.db.commit()

        recs = get_recommendations(self.db, "u001")
        self.assertEqual([r["content_id"] for r in recs], ["c002"])

    def test_falls_back_to_recent_when_nothing_matches(self):
        self._add_user("u001", [])  # no declared interests
        older = self.today - datetime.timedelta(days=2)
        self._add_content("c001", ["unrelated"], published_at=older)
        self._add_content("c002", ["unrelated"], published_at=self.today)
        self.db.commit()

        recs = get_recommendations(self.db, "u001")
        self.assertEqual([r["content_id"] for r in recs], ["c002", "c001"])
        self.assertEqual(recs[0]["reason_code"], "Recently published")

    def test_unknown_user_raises(self):
        with self.assertRaises(ValueError):
            get_recommendations(self.db, "u999")


if __name__ == "__main__":
    unittest.main()
