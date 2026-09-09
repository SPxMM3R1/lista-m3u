import os
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
        self.assertEqual(
            result.get("source-info-name"),
            "iptv-org/epg combinado + continuidad tecnica",
        )
        self.assertNotIn("epg-publicada-conservada", ET.tostring(result).decode())
        self.assertEqual(
            status["guide_sources"]["Meganoticias.cl"],
            "continuidad-tecnica",
        )

    def test_overlapping_programmes_are_trimmed_not_fatal(self):
        root = ET.Element("tv")
        ET.SubElement(root, "channel", {"id": "demo"})
        now = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
        for start, stop, title in (
            (now, now + timedelta(hours=2), "Primero"),
            (now + timedelta(hours=1), now + timedelta(hours=3), "Segundo"),
        ):
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format(start),
                    "stop": update_m3u.xmltv_format(stop),
                    "channel": "demo",
                },
            )
            ET.SubElement(programme, "title").text = title

        removed = update_m3u.normalize_xmltv_programmes(root, {"demo"})
        programmes = root.findall("programme")
        self.assertEqual(removed, 0)
        self.assertEqual(len(programmes), 2)
        first_stop = update_m3u.xmltv_datetime(programmes[0].get("stop", ""))
        second_start = update_m3u.xmltv_datetime(programmes[1].get("start", ""))
        self.assertEqual(first_stop, second_start)

    def test_refresh_uses_only_combined_guide_after_success(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        channel = update_m3u.Channel(
            name="TVN",
            url="https://example.invalid/tvn.m3u8",
            url_line=1,
            info_line=0,
            tvg_id="0104",
        )
        combined_root = ET.Element("tv")
        ET.SubElement(combined_root, "channel", {"id": "0104"})
        programme = ET.SubElement(
            combined_root,
            "programme",
            {
                "start": update_m3u.xmltv_format(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format(now + timedelta(days=2)),
                "channel": "0104",
            },
        )
        ET.SubElement(programme, "title").text = "Fuente combinada"
        old_root = ET.Element("tv")
        ET.SubElement(old_root, "channel", {"id": "0104"})
        old_programme = ET.SubElement(
            old_root,
            "programme",
            {
                "start": update_m3u.xmltv_format(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format(now + timedelta(days=2)),
                "channel": "0104",
            },
        )
        ET.SubElement(old_programme, "title").text = "Guia anterior"

        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            guide_path = directory / "combined.xml"
            epg_path = directory / "epg.xml"
            guide_path.write_bytes(
                ET.tostring(combined_root, encoding="utf-8", xml_declaration=True)
            )
            with patch.object(update_m3u, "EPG_PATH", epg_path), patch.dict(
                os.environ,
                {"IPTV_ORG_EPG_GUIDE_PATH": str(guide_path)},
            ):
                status = update_m3u.refresh_epg_from_iptv_org(
                    [channel],
                    now=now,
                    existing_status={"ok": True, "sources": ["old"]},
                    existing_data=ET.tostring(
                        old_root, encoding="utf-8", xml_declaration=True
                    ),
                )
            output = epg_path.read_bytes().decode("utf-8")

        self.assertEqual(status["sources"], [update_m3u.IPTV_ORG_EPG_SOURCE])
        self.assertTrue(status["single_source_pipeline"])
        self.assertNotIn("epg-publicada-conservada", output)
        self.assertNotIn("Guia anterior", output)
        self.assertIn("Fuente combinada", output)


if __name__ == "__main__":
    unittest.main()
