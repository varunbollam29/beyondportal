"""Unit tests for the Engagement Scoring Agent (#2) formula — see
CLAUDE.md Section 11.2: this is one of the two pieces of real business
logic that must be tested."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.signal_ingestion import update_engagement_score
from models import Base, SignalWeightConfig


class TestEngagementScoring(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.db.add(SignalWeightConfig(signal_type="ARTICLE_READ", weight=10))
        self.db.add(SignalWeightConfig(signal_type="VIDEO_WATCHED", weight=20))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_first_signal_from_zero(self):
        row = update_engagement_score(self.db, user_id="u001", signal_type="ARTICLE_READ", depth_pct=50)
        self.assertEqual(row.score, 5)
        self.assertEqual(row.delta, 5.0)
        self.assertEqual(row.level, "Getting Started")

    def test_accumulates_on_existing_score(self):
        update_engagement_score(self.db, user_id="u001", signal_type="ARTICLE_READ", depth_pct=100)
        row = update_engagement_score(self.db, user_id="u001", signal_type="VIDEO_WATCHED", depth_pct=100)
        self.assertEqual(row.score, 30)
        self.assertEqual(row.delta, 20.0)

    def test_caps_at_100(self):
        for _ in range(20):
            row = update_engagement_score(self.db, user_id="u001", signal_type="VIDEO_WATCHED", depth_pct=100)
        self.assertEqual(row.score, 100)

    def test_missing_weight_config_defaults_to_zero(self):
        row = update_engagement_score(self.db, user_id="u001", signal_type="ASK_AI_QUERY", depth_pct=None)
        self.assertEqual(row.score, 0)
        self.assertEqual(row.delta, 0.0)

    def test_no_depth_pct_uses_full_weight(self):
        row = update_engagement_score(self.db, user_id="u001", signal_type="ARTICLE_READ", depth_pct=None)
        self.assertEqual(row.score, 10)

    def test_level_thresholds(self):
        row = update_engagement_score(self.db, user_id="u002", signal_type="VIDEO_WATCHED", depth_pct=100)
        self.assertEqual(row.level, "Getting Started")  # 20
        for _ in range(2):
            row = update_engagement_score(self.db, user_id="u002", signal_type="VIDEO_WATCHED", depth_pct=100)
        self.assertEqual(row.score, 60)
        self.assertEqual(row.level, "Active")
        row = update_engagement_score(self.db, user_id="u002", signal_type="VIDEO_WATCHED", depth_pct=100)
        self.assertEqual(row.score, 80)
        self.assertEqual(row.level, "Very Active")


if __name__ == "__main__":
    unittest.main()
