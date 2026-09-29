import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import highfly_live
import update_m3u


def row(key="SkySportsF1.uk", name="SKY SPORTS F1", slug="now-545445", state="active"):
    return {"provider": "highfly", "catalogKey": key, "name": name,
            "resolverSlug": slug, "providerResourceId": f"leaf:{slug}", "state": state}


class HighflyLiveTest(unittest.TestCase):
    def test_publishes_the_editor_leaf_when_it_has_signal(self) -> None:
        document = highfly_live.build_document(
            [row()], fetch=lambda slug: ["https://papacito.cfd/m3u/x/live.m3u8"],
            now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))

        self.assertEqual([{"catalogKey": "SkySportsF1.uk", "slug": "now-545445",
                           "url": "https://papacito.cfd/m3u/now-545445/live.m3u8"}], document["channels"])
        self.assertEqual("2026-09-28T12:00:00Z", document["generatedAt"])

    def test_falls_back_to_another_leaf_of_the_same_channel(self) -> None:
        with patch.dict(update_m3u.HIGHFLY_RUNTIME_VARIANTS, {"skysportsf1": ["now-545445", "now-34343434"]}, clear=True):
            document = highfly_live.build_document(
                [row()], fetch=lambda slug: [] if slug == "now-545445" else ["ok"])
        self.assertEqual("now-34343434", document["channels"][0]["slug"])

    def test_channel_without_signal_is_not_published(self) -> None:
        document = highfly_live.build_document([row()], fetch=lambda slug: [])
        self.assertEqual([], document["channels"])

    def test_only_active_highfly_rows_are_used(self) -> None:
        layout = {"channels": [row(), row(key="X", state="trash"), {"provider": "tvvoo", "catalogKey": "Y"}]}
        self.assertEqual(["SkySportsF1.uk"], [r["catalogKey"] for r in highfly_live.active_highfly_rows(layout)])

    def test_published_link_carries_no_token(self) -> None:
        document = highfly_live.build_document([row()], fetch=lambda slug: ["ok"])
        url = document["channels"][0]["url"]
        self.assertTrue(update_m3u.is_highfly_leaf_url(url))
        self.assertNotIn("?", url)

    def test_timestamp_alone_does_not_rewrite_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "highfly-live.json"
            first = highfly_live.build_document([row()], fetch=lambda slug: ["ok"],
                                                now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))
            self.assertTrue(highfly_live.write_if_changed(first, path))
            later = highfly_live.build_document([row()], fetch=lambda slug: ["ok"],
                                                now=datetime(2026, 9, 28, 13, tzinfo=timezone.utc))
            self.assertFalse(highfly_live.write_if_changed(later, path))
            self.assertEqual("2026-09-28T12:00:00Z", json.loads(path.read_text(encoding="utf-8"))["generatedAt"])


if __name__ == "__main__":
    unittest.main()
