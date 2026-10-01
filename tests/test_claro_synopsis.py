import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import update_m3u
from epg_sources import claro


def event(start: datetime, minutes: int, name: str, description: str) -> dict:
    return {
        "unix_begin": int(start.timestamp()),
        "unix_end": int((start + timedelta(minutes=minutes)).timestamp()),
        "name": name,
        "description": description,
    }


class ClaroSynopsisTests(unittest.TestCase):
    now = datetime(2026, 10, 1, 20, tzinfo=timezone.utc)

    def test_only_useful_synopses_are_kept(self) -> None:
        payload = {"response": {"channels": [{"group_id": "908389", "events": [
            event(self.now, 60, "Caso Cerrado", "La doctora Ana María Polo resuelve casos legales reales."),
            event(self.now, 60, "Cine La Red", "Cine La Red"),
            event(self.now, 60, "CNN Chile", "Programación CNN Chile"),
            event(self.now, 60, "Corto", "Muy breve."),
        ]}]}}
        result = claro.claro_synopsis_programmes(payload, {"0104": "908389"})
        self.assertEqual(["Caso Cerrado"], [title for _, _, title, _ in result["0104"]])

    def test_claro_channels_are_description_only(self) -> None:
        for target_id in update_m3u.CLARO_SYNOPSIS_CHANNELS:
            self.assertNotIn(
                update_m3u.CLARO_SYNOPSIS_PART,
                [source for source, _ in update_m3u.epg_source_chain(target_id)],
            )
        self.assertIn(update_m3u.CLARO_SYNOPSIS_PART, update_m3u.epg_part_names())

    def _donate(self, shift: timedelta) -> str | None:
        root = ET.Element("tv")
        programme = ET.SubElement(root, "programme", {
            "start": update_m3u.xmltv_format_chile(self.now),
            "stop": update_m3u.xmltv_format_chile(self.now + timedelta(minutes=100)),
            "channel": "0107",
        })
        ET.SubElement(programme, "title").text = "Teletrece Central"
        donor = ET.Element("programme")
        ET.SubElement(donor, "title").text = "Teletrece"
        ET.SubElement(donor, "desc").text = "Noticiero central de Canal 13 con lo más importante del día."
        start = self.now + shift
        programmes_by_key = {
            (update_m3u.CLARO_SYNOPSIS_PART, update_m3u.ZAPPING_DESCRIPTION_ID_PREFIX + "0107"): [
                (start, start + timedelta(minutes=100), donor)
            ]
        }
        update_m3u.donate_epg_descriptions(root, programmes_by_key, {"0107"})
        return programme.findtext("desc")

    def test_shifted_guide_still_donates_the_same_airing(self) -> None:
        self.assertIsNotNone(self._donate(timedelta(minutes=100)))

    def test_another_days_airing_is_never_used(self) -> None:
        self.assertIsNone(self._donate(timedelta(hours=24)))


if __name__ == "__main__":
    unittest.main()
