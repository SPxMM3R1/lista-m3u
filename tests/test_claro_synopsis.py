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

    def test_titled_events_are_kept_and_synopsis_only_when_useful(self) -> None:
        # Los bloques con título siempre entran (p. ej. «Music Videos» de ETC TV
        # llenan la parrilla); la sinopsis se conserva solo si es útil.
        payload = {"response": {"channels": [{"group_id": "908389", "events": [
            event(self.now, 60, "Caso Cerrado", "La doctora Ana María Polo resuelve casos legales reales."),
            event(self.now, 60, "Cine La Red", "Cine La Red"),
            event(self.now, 60, "CNN Chile", "Programación CNN Chile"),
            event(self.now, 60, "Corto", "Muy breve."),
        ]}]}}
        result = claro.claro_synopsis_programmes(payload, {"0104": "908389"})
        self.assertEqual(
            ["Caso Cerrado", "Cine La Red", "CNN Chile", "Corto"],
            [title for _, _, title, _ in result["0104"]],
        )
        self.assertTrue(result["0104"][0][3])
        self.assertEqual("", result["0104"][1][3])

    def test_claro_channels_are_description_only(self) -> None:
        # Excepción cerrada (2026-10-13 TVN3; 2026-10-18 ETC TV): TVN3 usa la
        # parrilla de Claro como respaldo de horario (coincide con Zapping);
        # ETC TV la usa como fuente principal (verificada con fotogramas del
        # stream: la guía de Zapping para ETC no coincide con la señal).
        # 2026-10-21: Sony Movies #55 usa la parrilla de Claro Argentina
        # (verificada: el usuario vio «El Vengador Fantasma» a esa hora).
        self.assertEqual(
            frozenset({"1437", "PublicDirect.3ba5922c6040fadb816835b1",
                       "PublicDirect.376c74e4d0452f743fd2c811"}),
            update_m3u.CLARO_SCHEDULE_FALLBACK_IDS,
        )
        self.assertEqual(("argentina", "1151743"),
                         update_m3u.CLARO_REGION_CHANNELS["PublicDirect.376c74e4d0452f743fd2c811"])
        self.assertEqual(update_m3u.CLARO_SYNOPSIS_PART,
                         update_m3u.epg_source_chain("PublicDirect.376c74e4d0452f743fd2c811")[0][0])
        for target_id in update_m3u.CLARO_SYNOPSIS_CHANNELS:
            if target_id in update_m3u.CLARO_SCHEDULE_FALLBACK_IDS:
                continue
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
