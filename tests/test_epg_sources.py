import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import update_m3u
from epg_sources import red_bull

NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


class OfficialEpgSourcesTest(unittest.TestCase):
    """Cada fuente EPG oficial vive en epg_sources/ y falla sola."""

    def test_every_source_has_its_fetch_function(self) -> None:
        names = [source.name for source in update_m3u.OFFICIAL_EPG_SOURCES]
        self.assertEqual(len(names), len(set(names)))
        for source in update_m3u.OFFICIAL_EPG_SOURCES:
            fetch = getattr(update_m3u, source.fetch)
            self.assertTrue(fetch.__module__.startswith("epg_sources."), source.fetch)

    def test_a_crashing_source_does_not_stop_the_others(self) -> None:
        def quiet(*_args):
            return None, None

        patches = [
            patch.object(update_m3u, source.fetch, side_effect=quiet)
            for source in update_m3u.OFFICIAL_EPG_SOURCES
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        with patch.object(
            update_m3u, "fetch_tvn_official_epg", side_effect=RuntimeError("caida")
        ), patch.object(
            update_m3u, "fetch_la_red_official_epg", return_value=(b"<tv/>", None)
        ):
            documents, errors = update_m3u.fetch_official_epg_sources([], NOW)

        self.assertEqual({update_m3u.LA_RED_OFFICIAL_EPG_SOURCE: b"<tv/>"}, documents)
        self.assertEqual(
            {update_m3u.TVN_OFFICIAL_EPG_SOURCE: "RuntimeError: caida"}, errors
        )

    def test_la_red_replaces_only_its_listed_sources(self) -> None:
        lookup = {
            ("cl", "Canal.La.Red.(Chile).cl"): {"0102"},
            (update_m3u.ZAPPING_EPG_SOURCE, "0102"): {"0102"},
            ("otra", "compartida"): {"0102", "0999"},
        }
        update_m3u.prefer_official_epg_sources(
            lookup, [update_m3u.LA_RED_OFFICIAL_EPG_SOURCE], {"0102", "0999"}
        )
        self.assertEqual(
            {
                ("otra", "compartida"): {"0102", "0999"},
                (update_m3u.LA_RED_OFFICIAL_EPG_SOURCE, "0102"): {"0102"},
            },
            lookup,
        )

    def test_exclusive_source_replaces_every_other_source_of_the_channel(self) -> None:
        lookup = {("cl", "TVN"): {"0104"}, ("cl", "Mega"): {"0105"}}
        update_m3u.prefer_official_epg_sources(
            lookup, [update_m3u.TVN_OFFICIAL_EPG_SOURCE], {"0104", "0105"}
        )
        self.assertEqual(
            {
                ("cl", "Mega"): {"0105"},
                (update_m3u.TVN_OFFICIAL_EPG_SOURCE, "0104"): {"0104"},
            },
            lookup,
        )

    def test_unavailable_source_keeps_the_fallback(self) -> None:
        lookup = {("cl", "TVN"): {"0104"}}
        update_m3u.prefer_official_epg_sources(lookup, [], {"0104"})
        self.assertEqual({("cl", "TVN"): {"0104"}}, lookup)


class RedBullChileTest(unittest.TestCase):
    """Red Bull reparte la parrilla por país de la IP: fuera de Chile se usa la copia chilena."""

    def snapshot(self, country: str = "cl") -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "redbull-cl-epg.json"
        path.write_text(json.dumps({"schema": 1, "country": country, "programmes": [
            {"start_time": "2026-09-27T11:00:00Z", "end_time": "2026-09-27T13:00:00Z", "title": "Erzbergrodeo"},
            {"start_time": "2026-09-27T13:00:00Z", "end_time": "2026-09-27T14:00:00Z", "title": "Soapbox"},
        ]}), encoding="utf-8")
        return path

    def test_chilean_connection_reads_the_live_page(self) -> None:
        with patch.object(red_bull, "red_bull_request_country", return_value="cl"), patch.object(
            red_bull, "red_bull_page_schedule", return_value=["pagina"]
        ) as page:
            self.assertEqual(["pagina"], red_bull.red_bull_chile_schedule(NOW))
        page.assert_called_once()

    def test_foreign_connection_uses_the_chilean_snapshot_not_the_page(self) -> None:
        path = self.snapshot()
        with patch.object(red_bull, "red_bull_request_country", return_value="us"), patch.object(
            red_bull, "red_bull_page_schedule"
        ) as page, patch.object(red_bull, "RED_BULL_CHILE_EPG_SNAPSHOT_PATH", path), patch.object(
            red_bull.red_bull_chile_snapshot_schedule, "__defaults__", (path,)
        ):
            schedule = red_bull.red_bull_chile_schedule(NOW)
        page.assert_not_called()
        self.assertEqual(["Erzbergrodeo", "Soapbox"], [item["title"] for item in schedule])

    def test_foreign_connection_without_snapshot_publishes_nothing(self) -> None:
        missing = Path(tempfile.gettempdir()) / "no-existe-redbull-cl.json"
        with patch.object(red_bull, "red_bull_request_country", return_value="us"), patch.object(
            red_bull.red_bull_chile_snapshot_schedule, "__defaults__", (missing,)
        ):
            with self.assertRaisesRegex(ValueError, "'us'"):
                red_bull.red_bull_chile_schedule(NOW)

    def test_snapshot_from_another_country_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no es de Chile"):
            red_bull.red_bull_chile_snapshot_schedule(NOW, self.snapshot("us"))

    def test_expired_snapshot_is_rejected(self) -> None:
        later = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "vigentes"):
            red_bull.red_bull_chile_snapshot_schedule(later, self.snapshot())


if __name__ == "__main__":
    unittest.main()
