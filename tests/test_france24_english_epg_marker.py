"""The source language marker is not part of France 24 English's EPG display text."""
import unittest
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import update_m3u as runner


class France24EnglishEpgMarkerTests(unittest.TestCase):
    def test_marker_is_removed_from_visible_fields_only_for_english_channel(self):
        root = ET.Element("tv")
        english = ET.SubElement(
            root,
            "programme",
            {
                "channel": runner.FRANCE24_ENGLISH_EPG_CHANNEL_ID,
                "start": "20261012170000 +0000",
                "stop": "20261012173000 +0000",
            },
        )
        ET.SubElement(english, "title", {"lang": "en"}).text = (
            "Le journal France 24 (EN)"
        )
        ET.SubElement(english, "sub-title", {"lang": "en"}).text = (
            "Top stories ( en ) – édition spéciale"
        )
        ET.SubElement(english, "desc", {"lang": "en"}).text = (
            "Le programme (EN), toute l’actualité."
        )
        ET.SubElement(english, "category", {"lang": "en"}).text = "News (EN)"

        spanish = ET.SubElement(
            root,
            "programme",
            {
                "channel": "France24.fr",
                "start": "20261012170000 +0000",
                "stop": "20261012173000 +0000",
            },
        )
        spanish_title = ET.SubElement(spanish, "title", {"lang": "es"})
        spanish_title.text = "France 24 (EN)"

        _placeholder_channels, changed = runner.normalize_main_epg_schedule(
            root,
            {runner.FRANCE24_ENGLISH_EPG_CHANNEL_ID, "France24.fr"},
            now=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(changed)
        self.assertEqual("Le journal France 24", english.findtext("title"))
        self.assertEqual(
            "Top stories – édition spéciale", english.findtext("sub-title")
        )
        self.assertEqual(
            "Le programme, toute l’actualité.", english.findtext("desc")
        )
        self.assertEqual("News", english.findtext("category"))
        self.assertEqual("France 24 (EN)", spanish_title.text)
        self.assertFalse(
            any(
                "(EN)" in (element.text or "").upper()
                for element in english.iter()
                if element.tag in {"title", "sub-title", "desc", "category"}
            )
        )

    def test_marker_only_title_does_not_remain_visible(self):
        root = ET.Element("tv")
        programme = ET.SubElement(
            root,
            "programme",
            {"channel": runner.FRANCE24_ENGLISH_EPG_CHANNEL_ID},
        )
        ET.SubElement(programme, "title", {"lang": "en"}).text = "(EN)"

        runner.normalize_main_epg_schedule(
            root,
            {runner.FRANCE24_ENGLISH_EPG_CHANNEL_ID},
            now=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(runner.EPG_MAIN_FALLBACK_TITLE, programme.findtext("title"))
        self.assertNotIn("(EN)", programme.findtext("title", ""))


if __name__ == "__main__":
    unittest.main()
