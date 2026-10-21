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
