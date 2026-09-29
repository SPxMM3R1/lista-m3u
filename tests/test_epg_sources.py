import unittest
from datetime import datetime, timezone
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

    def test_official_source_leads_the_chain_and_others_fill(self) -> None:
        chain = update_m3u.epg_source_chain("0104")
        self.assertEqual(chain[0], (update_m3u.TVN_OFFICIAL_EPG_SOURCE, "0104"))
        self.assertIn(("tecnocentro", "LCH1225"), chain)
        self.assertEqual(chain[-1], (update_m3u.PUBLISHED_EPG_FALLBACK_SOURCE, "0104"))

    def test_replaced_keys_are_never_used(self) -> None:
        self.assertNotIn(("cl", "Canal.NHK.World.cl"), update_m3u.epg_source_chain("NHKWorldJapan.jp"))
        self.assertNotIn(
            (update_m3u.ZAPPING_EPG_SOURCE, "13C.cl@SD"), update_m3u.epg_source_chain("13C.cl@SD")
        )


class RedBullChileTest(unittest.TestCase):
    """Red Bull reparte la parrilla por país: se pide como visita chilena."""

    def test_page_and_session_are_requested_as_a_chilean_visit(self) -> None:
        headers = []

        def fake_fetch(url, request_headers, **_kwargs):
            headers.append(request_headers)
            return 200, b'{"country_code": "cl"}', {}

        with patch.object(red_bull, "fetch_bytes", side_effect=fake_fetch):
            self.assertEqual("cl", red_bull.red_bull_request_country())
        self.assertEqual(
            update_m3u.RED_BULL_CHILE_FORWARDED_FOR, headers[0]["X-Forwarded-For"]
        )

    def test_chilean_visit_reads_the_live_page(self) -> None:
        with patch.object(red_bull, "red_bull_request_country", return_value="cl"), patch.object(
            red_bull, "red_bull_page_schedule", return_value=["pagina"]
        ) as page:
            self.assertEqual(["pagina"], red_bull.red_bull_chile_schedule(NOW))
        page.assert_called_once()

    def test_other_country_publishes_nothing(self) -> None:
        with patch.object(red_bull, "red_bull_request_country", return_value="us"), patch.object(
            red_bull, "red_bull_page_schedule"
        ) as page:
            with self.assertRaisesRegex(ValueError, "'us'"):
                red_bull.red_bull_chile_schedule(NOW)
        page.assert_not_called()

if __name__ == "__main__":
    unittest.main()


class Canal13GoTimesTest(unittest.TestCase):
    def test_13go_seconds_round_to_contiguous_minutes(self) -> None:
        from epg_sources.canal13 import round_to_minute

        end = datetime(2026, 9, 30, 0, 58, 22, tzinfo=timezone.utc)
        next_start = datetime(2026, 9, 30, 0, 58, 23, tzinfo=timezone.utc)
        self.assertEqual(round_to_minute(end), round_to_minute(next_start))
        self.assertEqual(
            round_to_minute(datetime(2026, 9, 30, 0, 59, 30, tzinfo=timezone.utc)),
            datetime(2026, 9, 30, 1, 0, tzinfo=timezone.utc),
        )
