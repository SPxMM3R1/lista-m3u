import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import update_m3u  # noqa: E402


NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


class EpgPartsTest(unittest.TestCase):
    def test_every_official_source_is_its_own_part(self) -> None:
        names = update_m3u.epg_part_names()

        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], update_m3u.EPGSHARE_PART)
        for source in update_m3u.OFFICIAL_EPG_SOURCES:
            self.assertIn(source.name, names)
        for name in names:
            self.assertRegex(name, r"^[a-z0-9-]+$")

    def test_part_round_trips_through_disk(self) -> None:
        part = update_m3u.EpgPart(
            documents={"mega-oficial": "<tv>ñ</tv>".encode("utf-8")},
            errors={"zapping-guia-publica:0102": "HTTP 500"},
            red_bull_schedules={"RedBull.tv": [{"title": "Cliff", "end_time": "2026-09-29T13:00:00Z"}]},
            red_bull_source_names=["red_bull:cl"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            update_m3u.write_epg_part(directory, "mega-oficial", part)
            loaded = update_m3u.read_epg_part(directory, "mega-oficial")

        self.assertEqual(loaded, part)

    def test_damaged_or_foreign_part_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            update_m3u.write_epg_part(directory, "mega-oficial", update_m3u.EpgPart())
            update_m3u.epg_part_path(directory, "mega-oficial").rename(
                update_m3u.epg_part_path(directory, "tvn-oficial")
            )
            update_m3u.epg_part_path(directory, "sky-oficial").write_bytes(b"no es gzip")

            self.assertIsNone(update_m3u.read_epg_part(directory, "tvn-oficial"))
            self.assertIsNone(update_m3u.read_epg_part(directory, "sky-oficial"))
            self.assertIsNone(update_m3u.read_epg_part(directory, "la-red-oficial"))

    def test_missing_parts_become_isolated_errors_in_a_full_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            update_m3u.write_epg_part(
                directory,
                "mega-oficial",
                update_m3u.EpgPart(documents={"mega-oficial": b"<tv/>"}),
            )
            parts = update_m3u.collect_epg_parts([], set(), NOW, parts_dir=directory)
            partial = update_m3u.collect_epg_parts(
                [], set(), NOW, parts_dir=directory, parts_only=True
            )

        self.assertEqual(set(parts), set(update_m3u.epg_part_names()))
        self.assertEqual(parts["mega-oficial"].documents, {"mega-oficial": b"<tv/>"})
        self.assertIn("tvn-oficial", parts["tvn-oficial"].errors)
        self.assertIn("red_bull:todas", parts["red-bull"].errors)
        self.assertIn("zapping-guia-publica:todas", parts["zapping-guia-publica"].errors)
        self.assertIn(update_m3u.EPGSHARE_PART, parts[update_m3u.EPGSHARE_PART].errors)
        # Corrida de una sola fuente: lo que falta conserva la guía publicada.
        self.assertEqual(set(partial), {"mega-oficial"})

    def test_official_part_crash_stays_inside_that_part(self) -> None:
        def boom(*_args):
            raise RuntimeError("se cayó")

        with patch.object(update_m3u, "fetch_mega_official_epg", boom):
            part = update_m3u.fetch_epg_part("mega-oficial", [], set(), NOW)

        self.assertEqual(part.documents, {})
        self.assertIn("se cayó", part.errors["mega-oficial"])

    def test_fetch_retries_and_keeps_the_best_attempt(self) -> None:
        attempts = [
            update_m3u.EpgPart(errors={"mega-oficial": "HTTP 503"}),
            update_m3u.EpgPart(documents={"mega-oficial": b"<tv/>"}),
        ]
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            update_m3u, "epg_scope_channels", return_value=([], set())
        ), patch.object(
            update_m3u, "fetch_epg_part", side_effect=lambda *_args: attempts.pop(0)
        ), patch.object(update_m3u.time, "sleep"):
            directory = Path(temporary)
            code = update_m3u.fetch_epg_part_to_dir("mega-oficial", directory)
            loaded = update_m3u.read_epg_part(directory, "mega-oficial")

        self.assertEqual(code, 0)
        self.assertEqual(loaded.documents, {"mega-oficial": b"<tv/>"})
        self.assertEqual(loaded.errors, {})

    def test_unknown_part_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(
                update_m3u.fetch_epg_part_to_dir("no-existe", Path(temporary)), 2
            )


class EpgPendingDetailsTest(unittest.TestCase):
    def test_pending_channels_are_classified_by_what_is_missing(self) -> None:
        from datetime import timedelta
        import xml.etree.ElementTree as ET

        root = ET.Element("tv")

        def programme(channel_id, start_h, stop_h):
            ET.SubElement(root, "programme", {
                "channel": channel_id,
                "start": update_m3u.xmltv_format_chile(NOW + timedelta(hours=start_h)),
                "stop": update_m3u.xmltv_format_chile(NOW + timedelta(hours=stop_h)),
            })

        programme("corta", -1, 3)
        programme("hueco", 1, 40)  # fuera del aire la primera hora
        details = update_m3u.epg_pending_details(
            root, ["corta", "hueco", "vacia"], now=NOW, main_ids={"corta", "hueco", "vacia"}
        )

        self.assertEqual(details["vacia"]["kind"], "sin-guia")
        self.assertEqual(details["corta"]["kind"], "guia-corta")
        self.assertEqual(details["corta"]["futureHours"], 3.0)
        self.assertEqual(details["corta"]["gaps"], [])
        self.assertEqual(details["hueco"]["kind"], "hueco")
        self.assertEqual(details["hueco"]["gaps"], [["2026-09-29T12:00:00Z", "2026-09-29T13:00:00Z"]])
        self.assertEqual(details["hueco"]["requiredHours"], 18.0)


if __name__ == "__main__":
    unittest.main()
