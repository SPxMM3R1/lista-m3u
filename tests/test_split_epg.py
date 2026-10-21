"""Guía separada por lista (2026-10-21): epg.xml para Lista 1, epg-2.xml para Lista 2."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import update_m3u

ROOT = Path(__file__).resolve().parents[1]

SAMPLE = b"""<?xml version='1.0' encoding='utf-8'?>
<tv data-epg-scope="m3u.m3u">
  <channel id="uno"><display-name>Uno</display-name></channel>
  <channel id="dos"><display-name>Dos</display-name></channel>
  <channel id="alias-dos" data-app-alias-of="dos"><display-name>Dos</display-name></channel>
  <programme start="20261021120000 +0000" stop="20261021130000 +0000" channel="uno"><title>A</title></programme>
  <programme start="20261021120000 +0000" stop="20261021130000 +0000" channel="dos"><title>B</title></programme>
  <programme start="20261021120000 +0000" stop="20261021130000 +0000" channel="alias-dos"><title>B</title></programme>
</tv>
"""


class SplitEpgTests(unittest.TestCase):
    def test_list2_channels_and_their_aliases_go_to_the_second_guide(self) -> None:
        first, second = update_m3u.split_epg_documents(SAMPLE, {"dos"})
        one = ET.fromstring(first)
        two = ET.fromstring(second)
        self.assertEqual(["uno"], [c.get("id") for c in one.findall("channel")])
        self.assertEqual(["uno"], [p.get("channel") for p in one.findall("programme")])
        self.assertEqual({"dos", "alias-dos"}, {c.get("id") for c in two.findall("channel")})
        self.assertEqual(2, len(two.findall("programme")))
        self.assertEqual("m3u-externa.m3u", two.get("data-epg-scope"))

    def test_each_published_list_points_to_its_own_guide(self) -> None:
        for name, url in (
            ("m3u.m3u", update_m3u.EPG_PUBLIC_URL),
            ("1.m3u", update_m3u.EPG_PUBLIC_URL),
            ("m3u-externa.m3u", update_m3u.EPG2_PUBLIC_URL),
            ("2.m3u", update_m3u.EPG2_PUBLIC_URL),
        ):
            header = (ROOT / name).read_text(encoding="utf-8-sig").splitlines()[0]
            self.assertIn(f'x-tvg-url="{url}"', header, name)

    def test_published_guides_do_not_overlap(self) -> None:
        first = ET.parse(ROOT / "epg.xml").getroot()
        second = ET.parse(ROOT / "epg-2.xml").getroot()
        one = {c.get("id") for c in first.findall("channel")}
        two = {c.get("id") for c in second.findall("channel")}
        self.assertFalse(one & two)
        self.assertTrue(one)


if __name__ == "__main__":
    unittest.main()


class SharedGuideTests(unittest.TestCase):
    """2026-10-21: epg-2.xml guarda cada guía idéntica una sola vez (data-guide-of)."""

    DOC = b"""<?xml version='1.0' encoding='utf-8'?>
<tv>
  <channel id="a"><display-name>A</display-name></channel>
  <channel id="b"><display-name>B</display-name></channel>
  <channel id="c"><display-name>C</display-name></channel>
  <programme start="20261021120000 +0000" stop="20261021130000 +0000" channel="a"><title>X</title></programme>
  <programme start="20261021120000 +0000" stop="20261021130000 +0000" channel="b"><title>X</title></programme>
  <programme start="20261021120000 +0000" stop="20261021130000 +0000" channel="c"><title>Y</title></programme>
</tv>
"""

    def test_identical_guides_are_stored_once_and_expand_back(self) -> None:
        root = ET.fromstring(self.DOC)
        self.assertEqual(1, update_m3u.dedupe_shared_guides(root))
        channels = {c.get("id"): c for c in root.findall("channel")}
        self.assertEqual("a", channels["b"].get("data-guide-of"))
        self.assertEqual(["a", "c"], [p.get("channel") for p in root.findall("programme")])
        update_m3u.expand_shared_guides(root)
        self.assertEqual({"a", "b", "c"}, {p.get("channel") for p in root.findall("programme")})
        self.assertIsNone(root.find("channel[@id='b']").get("data-guide-of"))

    def test_list_one_guide_is_never_shared(self) -> None:
        first, second = update_m3u.split_epg_documents(self.DOC, {"b", "c"})
        self.assertNotIn(b"data-guide-of", first)
        self.assertNotIn(b"data-guide-of", second)  # b y c tienen guías distintas
