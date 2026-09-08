import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import update_m3u


class IptvOrgEpgContractTests(unittest.TestCase):
    def test_manifest_has_unique_stable_ids_and_known_sites(self):
        manifest = ET.parse(
            Path(__file__).resolve().parents[1] / update_m3u.IPTV_ORG_CHANNEL_MANIFEST
        ).getroot()
        channels = manifest.findall("channel")
        ids = [channel.get("xmltv_id") for channel in channels]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(channel.get("site_id") for channel in channels))
        self.assertTrue(
            all(channel.get("site") in {"epgshare01.online", "plex.tv"} for channel in channels)
        )

    def test_combined_guide_uses_tvg_ids_and_keeps_list_one_complete(self):
        channels = update_m3u.load_main_epg_channels()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        source_root = ET.Element("tv")
        for channel_id in ("0104", "SonyChannelAndes.us@SD"):
            ET.SubElement(source_root, "channel", {"id": channel_id})
            programme = ET.SubElement(
                source_root,
                "programme",
                {
                    "start": update_m3u.xmltv_format(now - timedelta(hours=1)),
                    "stop": update_m3u.xmltv_format(now + timedelta(days=2)),
                    "channel": channel_id,
                },
            )
            ET.SubElement(programme, "title").text = "Prueba de iptv-org/epg"

        output, status = update_m3u.build_epg(
            {
                update_m3u.IPTV_ORG_EPG_SOURCE: ET.tostring(
                    source_root, encoding="utf-8", xml_declaration=True
                )
            },
            channels,
            {},
            now=now,
        )
        result = ET.fromstring(output)
        output_ids = {element.get("id") for element in result.findall("channel")}
        programme_ids = {
            element.get("channel") for element in result.findall("programme")
        }
        expected_ids = {channel.tvg_id for channel in channels}
        self.assertEqual(output_ids, expected_ids)
        self.assertTrue({"0104", "SonyChannelAndes.us@SD"} <= programme_ids)
        self.assertTrue(status["ok"])


if __name__ == "__main__":
    unittest.main()
