import json
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from unittest.mock import patch

import update_m3u
from epg_sources import red_bull, tnt_sports

NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


class OfficialEpgSourcesTest(unittest.TestCase):
    # Estas pruebas usan TVN (0104) como ejemplo de fuente oficial. Desde 2026-11-22 el 0104
    # publicado usa GatoTV con "primary"; aquí se fija la cadena base (oficial, Zapping, CL).
    def setUp(self):
        original = update_m3u.apply_epg_overrides

        def base_tvn():
            update_m3u.EPG_PROGRAMME_SOURCES["0104"] = ("cl", "Canal.TVN.(Chile).cl")
            update_m3u.GATOTV_CHANNELS.pop("0104", None)
            update_m3u.EPG_OVERRIDE_PRIMARY_IDS.discard("0104")

        def wrapped(*args, **kwargs):
            result = original(*args, **kwargs)
            base_tvn()
            return result

        for patcher in (patch.dict(update_m3u.EPG_PROGRAMME_SOURCES),
                        patch.dict(update_m3u.GATOTV_CHANNELS),
                        patch.object(update_m3u, "EPG_OVERRIDE_PRIMARY_IDS", set()),
                        patch.object(update_m3u, "apply_epg_overrides", wrapped)):
            patcher.start()
            self.addCleanup(patcher.stop)
        base_tvn()
        super().setUp()

    """Cada fuente EPG oficial vive en epg_sources/ y falla sola."""

    def test_tnt_premium_uses_only_chile_feed_and_provider_offset(self):
        show = {"title": "", "originalTitle": "Partido", "begin": "2026-11-16T07:35:00",
                "end": "2026-11-16T09:40:00"}
        body = json.dumps({
            "com.turner.dmtla.schedule.dto.ScheduleDTO": {
                "offset": "-03:00", "feeds": [
                    {"code": "OTHER", "shows": [{**show, "originalTitle": "Otra señal"}]},
                    {"code": "CDFH_CL", "shows": [show, show]},
                ],
            },
        }).encode()
        with patch.object(tnt_sports, "fetch_bytes", return_value=(200, body, {})):
            data, error = tnt_sports.fetch_tnt_sports_premium_epg(
                [type("Target", (), {"tvg_id": tnt_sports.TARGET})()], NOW
            )
        self.assertIsNone(error)
        programme, = ET.fromstring(data).findall("programme")
        self.assertEqual("20261116073500 -0300", programme.get("start"))
        self.assertEqual("Partido", programme.findtext("title"))
        self.assertEqual(("tnt-sports-premium-oficial", "CDFH_CL"),
                         update_m3u.epg_source_chain(tnt_sports.TARGET)[0])

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

    def test_incomplete_official_guide_only_fills_after_zapping_and_tecnocentro(self) -> None:
        chain = update_m3u.epg_source_chain("0106")
        self.assertEqual(chain[0], (update_m3u.ZAPPING_EPG_SOURCE, "0106"))
        self.assertEqual(chain[1], ("tecnocentro", "LCH481"))
        self.assertEqual(chain[2], (update_m3u.CHV_OFFICIAL_EPG_SOURCE, "0106"))
        self.assertEqual(chain[-1], (update_m3u.PUBLISHED_EPG_FALLBACK_SOURCE, "0106"))

    def test_dsports_continues_with_the_uruguayan_feed_after_the_andean_one(self) -> None:
        chain = update_m3u.epg_source_chain("DSports.us@Direct15")
        andean = ("co1", "DSPORTS.(COL).(DTSC).co")
        uruguayan = ("uy1", "[SPOARHD].DSports.Argentina.HD.uy")
        self.assertIn(andean, chain)
        self.assertIn(uruguayan, chain)
        self.assertLess(chain.index(andean), chain.index(uruguayan))

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


class RedBullWorldTest(unittest.TestCase):
    """TV World (BoRB-AT): API global y relay; 2026-11-07 la página en_CL daba otra rail."""

    def test_world_reads_the_global_api(self) -> None:
        with patch.object(red_bull, "red_bull_api_schedule", return_value=["api"]) as api, \
                patch.object(red_bull, "red_bull_page_schedule") as page:
            schedules, sources, errors = red_bull.fetch_red_bull_schedules(
                {update_m3u.RED_BULL_WORLD_ID}, NOW)
        self.assertEqual({update_m3u.RED_BULL_WORLD_ID: ["api"]}, schedules)
        self.assertEqual({"red-bull-oficial"}, sources)
        self.assertEqual({}, errors)
        api.assert_called_once_with("en")
        page.assert_not_called()

    def test_world_falls_back_to_the_relay(self) -> None:
        with patch.object(red_bull, "red_bull_api_schedule", side_effect=ValueError("caida")), \
                patch.object(red_bull, "red_bull_relay_schedule", return_value=["relay"]):
            schedules, sources, errors = red_bull.fetch_red_bull_schedules(
                {update_m3u.RED_BULL_WORLD_ID}, NOW)
        self.assertEqual({update_m3u.RED_BULL_WORLD_ID: ["relay"]}, schedules)
        self.assertEqual({"red-bull-relay"}, sources)
        self.assertEqual({}, errors)

    def test_world_has_no_pluto_backup(self) -> None:
        self.assertNotIn(
            ("pluto", "5e7cb84a172a0f0007da69e4"),
            update_m3u.epg_source_chain(update_m3u.RED_BULL_WORLD_ID),
        )

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
