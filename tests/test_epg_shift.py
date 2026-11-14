"""Desfase fijo por canal (shift_minutes en epg-overrides.json).

2026-11-14, pedido del usuario: «TNT tiene un error de 10 minutos en la guía, se muestra antes».
La guía Claro del canal marca cada programa unos minutos antes de que empiece; el desfase corre
todos sus programas, pero no la guía publicada anterior (ya viene corrida).
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import update_m3u

TARGET = "Prueba.Desfase@Test"
NOW = datetime(2026, 11, 14, 13, 0, tzinfo=timezone.utc)


def channel():
    return update_m3u.Channel(name="TNT", display_name="TNT", tvg_id=TARGET,
                              url="https://example.invalid/live.m3u8", url_line=0)


def guide(channel_id, slots):
    root = ET.Element("tv")
    for start, stop, title in slots:
        programme = ET.SubElement(root, "programme", {
            "start": (NOW + timedelta(minutes=start)).strftime("%Y%m%d%H%M%S +0000"),
            "stop": (NOW + timedelta(minutes=stop)).strftime("%Y%m%d%H%M%S +0000"),
            "channel": channel_id})
        ET.SubElement(programme, "title").text = title
    return ET.tostring(root)


def spans(output):
    result = []
    for programme in ET.fromstring(output).findall("programme"):
        if programme.get("channel") == TARGET:
            start = update_m3u.xmltv_datetime(programme.get("start"))
            stop = update_m3u.xmltv_datetime(programme.get("stop"))
            result.append((programme.findtext("title"), int((start - NOW) / timedelta(minutes=1)),
                           int((stop - NOW) / timedelta(minutes=1))))
    return result


class EpgShiftTest(unittest.TestCase):
    def build(self, shift):
        sources = {TARGET: ("mx1", "Canal.Prueba.mx")}
        shifts = {TARGET: timedelta(minutes=shift)} if shift else {}
        with patch.dict(update_m3u.EPG_PROGRAMME_SOURCES, sources), \
                patch.dict(update_m3u.EPG_SHIFT_BY_TARGET, shifts, clear=True):
            output, _status = update_m3u.build_epg(
                {"mx1": guide("Canal.Prueba.mx", [(0, 120, "El juego del crimen"),
                                                   (120, 245, "Sing")])},
                [channel()], {}, now=NOW)
        return spans(output)

    def test_shift_moves_every_programme(self):
        self.assertEqual([("El juego del crimen", 0, 120), ("Sing", 120, 245)], self.build(0))
        self.assertEqual([("El juego del crimen", 10, 130), ("Sing", 130, 255)], self.build(10))

    def test_published_fallback_is_not_shifted_twice(self):
        previous = guide(TARGET, [(10, 130, "El juego del crimen")])
        with patch.dict(update_m3u.EPG_PROGRAMME_SOURCES, {TARGET: ("mx1", "Canal.Prueba.mx")}), \
                patch.dict(update_m3u.EPG_SHIFT_BY_TARGET, {TARGET: timedelta(minutes=10)}, clear=True):
            output, _status = update_m3u.build_epg(
                {update_m3u.PUBLISHED_EPG_FALLBACK_SOURCE: previous}, [channel()], {}, now=NOW)
        self.assertEqual([("El juego del crimen", 10, 130)], spans(output))

    def test_override_reads_and_validates_shift_minutes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "epg-overrides.json"
            with patch.dict(update_m3u.EPG_SHIFT_BY_TARGET, clear=True), \
                    patch.dict(update_m3u.EPG_PROGRAMME_SOURCES), \
                    patch.dict(update_m3u.EPGSHARE_BACKUP_CHANNELS):
                path.write_text(json.dumps({"channels": {TARGET: {
                    "source": "mx1", "source_id": "Canal.Prueba.mx", "shift_minutes": 10}}}),
                    encoding="utf-8")
                update_m3u.apply_epg_overrides(path)
                self.assertEqual(timedelta(minutes=10), update_m3u.EPG_SHIFT_BY_TARGET[TARGET])
                for bad in (0, 500, "10", True):
                    path.write_text(json.dumps({"channels": {TARGET: {
                        "source": "mx1", "source_id": "Canal.Prueba.mx", "shift_minutes": bad}}}),
                        encoding="utf-8")
                    with self.assertRaises(ValueError):
                        update_m3u.apply_epg_overrides(path)


if __name__ == "__main__":
    unittest.main()
