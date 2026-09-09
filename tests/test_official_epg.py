import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import update_m3u


class OfficialEpgContractTests(unittest.TestCase):
    def test_official_build_keeps_list_one_complete_with_live_fallback(self):
        channels = update_m3u.load_main_epg_channels()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        source_root = ET.Element("tv")
        ET.SubElement(source_root, "channel", {"id": "0104"})
        programme = ET.SubElement(
            source_root,
            "programme",
            {
                "start": update_m3u.xmltv_format(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format(now + timedelta(days=2)),
                "channel": "0104",
            },
        )
        ET.SubElement(programme, "title").text = "TVN oficial"

        output, status = update_m3u.build_epg(
            {
                update_m3u.TVN_OFFICIAL_EPG_SOURCE: ET.tostring(
                    source_root, encoding="utf-8", xml_declaration=True
                )
            },
            channels,
            {},
            now=now,
        )
        result = ET.fromstring(output)
        expected_ids = {channel.tvg_id for channel in channels}
        output_ids = {element.get("id") for element in result.findall("channel")}
        programme_ids = {
            element.get("channel") for element in result.findall("programme")
        }
        self.assertEqual(output_ids, expected_ids)
        self.assertEqual(status["guide_sources"]["0104"], update_m3u.TVN_OFFICIAL_EPG_SOURCE)
        self.assertTrue(expected_ids <= programme_ids)
        self.assertTrue(status["ok"])
        self.assertEqual(
            result.get("source-info-name"),
            "fuentes oficiales por canal + continuidad tecnica",
        )

    def test_official_source_takes_priority_for_exact_channel_id(self):
        channels = [
            update_m3u.Channel(
                name="TVN",
                url="https://example.invalid/tvn.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="0104",
            )
        ]
        now = datetime.now(timezone.utc).replace(microsecond=0)
        official_root = ET.Element("tv")
        ET.SubElement(official_root, "channel", {"id": "0104"})
        official_programme = ET.SubElement(
            official_root,
            "programme",
            {
                "start": update_m3u.xmltv_format(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format(now + timedelta(days=2)),
                "channel": "0104",
            },
        )
        ET.SubElement(official_programme, "title").text = "Fuente oficial"

        output, status = update_m3u.build_epg(
            {
                update_m3u.TVN_OFFICIAL_EPG_SOURCE: ET.tostring(
                    official_root, encoding="utf-8", xml_declaration=True
                )
            },
            channels,
            {},
            now=now,
        )
        result = ET.fromstring(output)
        self.assertEqual(status["guide_sources"]["0104"], update_m3u.TVN_OFFICIAL_EPG_SOURCE)
        self.assertIn("Fuente oficial", ET.tostring(result).decode("utf-8"))

    def test_official_refresh_does_not_reuse_previous_provider_guide(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        channel = update_m3u.Channel(
            name="TVN",
            url="https://example.invalid/tvn.m3u8",
            url_line=1,
            info_line=0,
            tvg_id="0104",
        )
        official_root = ET.Element("tv")
        ET.SubElement(official_root, "channel", {"id": "0104"})
        official_programme = ET.SubElement(
            official_root,
            "programme",
            {
                "start": update_m3u.xmltv_format(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format(now + timedelta(days=2)),
                "channel": "0104",
            },
        )
        ET.SubElement(official_programme, "title").text = "Fuente oficial nueva"

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
        ET.SubElement(old_programme, "title").text = "Fuente antigua no permitida"

        with TemporaryDirectory() as temporary:
            epg_path = Path(temporary) / "epg.xml"
            with patch.object(update_m3u, "EPG_PATH", epg_path), patch.object(
                update_m3u,
                "fetch_list1_official_epg",
                return_value=(
                    {update_m3u.TVN_OFFICIAL_EPG_SOURCE: ET.tostring(
                        official_root, encoding="utf-8", xml_declaration=True
                    )},
                    {},
                    set(),
                    {},
                ),
            ):
                status = update_m3u.refresh_epg_from_official(
                    [channel],
                    now=now,
                    existing_status={"ok": True},
                    existing_data=ET.tostring(
                        old_root, encoding="utf-8", xml_declaration=True
                    ),
                )
            output = epg_path.read_bytes().decode("utf-8")

        self.assertTrue(status["official_only_pipeline"])
        self.assertEqual(status["official_channel_ids"], ["0104"])
        self.assertIn("Fuente oficial nueva", output)
        self.assertNotIn("Fuente antigua no permitida", output)

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

    def test_official_mode_never_uses_red_bull_relay(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with patch.object(update_m3u, "EPG_SOURCE_MODE", "official-only"), patch.object(
            update_m3u,
            "red_bull_api_schedule",
            side_effect=ValueError("API oficial no disponible"),
        ), patch.object(
            update_m3u,
            "red_bull_relay_schedule",
            side_effect=AssertionError("no debe usarse el relay en official-only"),
        ):
            schedules, sources, errors = update_m3u.fetch_red_bull_schedules(
                {update_m3u.RED_BULL_WORLD_ID}, now
            )

        self.assertEqual(schedules, {})
        self.assertEqual(sources, set())
        self.assertIn(f"red_bull:{update_m3u.RED_BULL_WORLD_ID}", errors)


if __name__ == "__main__":
    unittest.main()
