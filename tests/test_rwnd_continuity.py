"""Rwnd: continuidad Live sin parrilla ni metadatos de otras señales."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import update_m3u


TARGET = update_m3u.EPG_MAIN_LIVE_CHANNEL_ID
NOW = datetime(2026, 10, 6, 22, tzinfo=timezone.utc)


def programme(root, channel_id, title="Programa ajeno"):
    item = ET.SubElement(root, "programme", {
        "channel": channel_id,
        "start": update_m3u.xmltv_format_chile(NOW),
        "stop": update_m3u.xmltv_format_chile(NOW + timedelta(hours=24)),
    })
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "desc").text = "Sinopsis de una señal que no es Rwnd."
    ET.SubElement(item, "sub-title").text = "Episodio ajeno"
    ET.SubElement(item, "category").text = "Drama"
    return item


class RwndContinuityTests(unittest.TestCase):
    def test_no_source_or_epgshare_download_even_with_source_override(self):
        self.assertNotIn(TARGET, update_m3u.EPG_PROGRAMME_SOURCES)
        channel = update_m3u.Channel(name="RWND", tvg_id=TARGET,
                                     url="https://example.invalid/live.m3u8", url_line=0)
        with patch.dict(update_m3u.EPG_PROGRAMME_SOURCES,
                        {TARGET: ("us2", "Rewind.TV.us2")}):
            self.assertEqual([], update_m3u.epg_source_chain(TARGET))
            self.assertEqual(frozenset(), update_m3u.epgshare_source_names_for([channel]))

    def test_build_ignores_fresh_foreign_guide_and_published_fallback(self):
        foreign, previous = ET.Element("tv"), ET.Element("tv")
        programme(foreign, "Rewind.TV.us2")
        programme(previous, TARGET)
        channel = update_m3u.Channel(name="RWND", tvg_id=TARGET,
                                     url="https://example.invalid/live.m3u8", url_line=0)
        output, status = update_m3u.build_epg(
            {"us2": ET.tostring(foreign),
             update_m3u.PUBLISHED_EPG_FALLBACK_SOURCE: ET.tostring(previous)},
            [channel], {}, now=NOW, coverage_required_ids={TARGET})
        root = ET.fromstring(output)
        items = root.findall("programme")
        self.assertEqual(3, len(items))
        for item in items:
            self.assertEqual(TARGET, item.get("channel"))
            self.assertEqual(["title"], [child.tag for child in item])
            self.assertEqual("Live", item.findtext("title"))
        self.assertEqual(NOW, update_m3u.xmltv_datetime(items[0].get("start")))
        self.assertEqual(NOW + update_m3u.EPG_MAIN_CONTINUITY_BUFFER,
                         update_m3u.xmltv_datetime(items[-1].get("stop")))
        self.assertEqual("rewind-continuous", status["guide_sources"][TARGET])
        self.assertEqual([], update_m3u.epg_coverage_gaps(
            root, {TARGET}, now=NOW, minimum_future=update_m3u.EPG_MAIN_MINIMUM_FUTURE))

    def test_reused_guide_is_cleaned_idempotently_without_touching_other_channels(self):
        root = ET.Element("tv")
        ET.SubElement(root, "channel", {"id": TARGET})
        rwnd = programme(root, TARGET)
        other = programme(root, "0104", "Noticias")
        preserved = ET.tostring(other)
        _, changed = update_m3u.normalize_main_epg_schedule(root, {TARGET, "0104"}, now=NOW)
        self.assertTrue(changed)
        self.assertEqual(["title"], [child.tag for child in rwnd])
        self.assertEqual("Live", rwnd.findtext("title"))
        self.assertEqual(preserved, ET.tostring(other))
        self.assertFalse(update_m3u.normalize_main_epg_schedule(
            root, {TARGET, "0104"}, now=NOW)[1])

    def test_synopsis_donors_cannot_describe_live_continuity(self):
        root, donor_root = ET.Element("tv"), ET.Element("tv")
        item = programme(root, TARGET, "Live")
        item.remove(item.find("desc"))
        donor = programme(donor_root, "sinopsis:" + TARGET, "Live")
        keys = {(source, "sinopsis:" + TARGET): [
            (NOW, NOW + timedelta(hours=24), donor)]
            for source in (update_m3u.ZAPPING_EPG_SOURCE, update_m3u.CLARO_SYNOPSIS_PART)}
        self.assertEqual(0, update_m3u.donate_epg_descriptions(root, keys, {TARGET}))
        self.assertIsNone(item.find("desc"))

    def test_manual_override_cannot_reintroduce_schedule(self):
        root, overrides = ET.Element("tv"), ET.Element("tv")
        for document in (root, overrides):
            ET.SubElement(document, "channel", {"id": TARGET})
        live = ET.SubElement(root, "programme", {
            "channel": TARGET, "start": "20261006220000 +0000", "stop": "20261007040000 +0000"})
        ET.SubElement(live, "title").text = "Live"
        programme(overrides, TARGET)
        data = ET.tostring(root)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overrides.xml"
            path.write_bytes(ET.tostring(overrides))
            self.assertEqual(data, update_m3u.apply_epg_manual_overrides(
                data, path, allowed_ids={TARGET}))


if __name__ == "__main__":
    unittest.main()
