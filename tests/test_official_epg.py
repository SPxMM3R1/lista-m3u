import unittest
import gzip
import json
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import update_m3u


class OfficialEpgContractTests(unittest.TestCase):
    @staticmethod
    def _xmltv_for_source_channel(source_channel_id, now, title_prefix):
        root = ET.Element("tv")
        ET.SubElement(root, "channel", {"id": source_channel_id})
        for index in range(6):
            start = now - timedelta(hours=1) + timedelta(hours=6 * index)
            stop = start + timedelta(hours=6)
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format(start),
                    "stop": update_m3u.xmltv_format(stop),
                    "channel": source_channel_id,
                },
            )
            ET.SubElement(programme, "title").text = f"{title_prefix} {index}"
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def test_official_page_retries_with_curl_after_urllib_error(self):
        url = "https://www.mega.cl/programacion/"
        headers = {
            "User-Agent": update_m3u.BROWSER_USER_AGENT,
            "Accept": "text/html,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9",
            "Referer": url,
        }
        urllib_error = urllib.error.HTTPError(
            url,
            404,
            "Not Found",
            {},
            None,
        )
        with patch.object(update_m3u, "fetch_bytes", side_effect=urllib_error), patch.object(
            update_m3u.subprocess,
            "run",
            return_value=SimpleNamespace(stdout=b"<html>pagina oficial</html>"),
        ) as curl_run:
            body = update_m3u.fetch_official_page_bytes(
                url,
                headers,
                timeout=60,
                limit=1024,
            )

        self.assertEqual(body, b"<html>pagina oficial</html>")
        command = curl_run.call_args.args[0]
        self.assertEqual(command[0], "curl")
        self.assertIn(url, command)
        self.assertIn("Referer: https://www.mega.cl/programacion/", command)

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
            "fuentes oficiales por canal + continuidad tecnica solo RWND",
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

    def test_epgshare_fetch_is_exact_and_requires_24_hours(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        channels = [
            update_m3u.Channel(
                name="24 Horas",
                url="https://example.invalid/24h.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="0201",
            )
        ]
        payload = self._xmltv_for_source_channel(
            "Canal.24.Horas.(Chile).cl",
            now,
            "24 Horas EPGShare",
        )

        def fake_fetch(url, headers, **kwargs):
            self.assertEqual(url, update_m3u.EPGSHARE_FALLBACK_URLS["cl"])
            self.assertEqual(kwargs["timeout"], 60)
            return 200, gzip.compress(payload), url

        with patch.object(update_m3u, "fetch_bytes", side_effect=fake_fetch):
            documents, errors = update_m3u.fetch_epgshare_fallback_epg(
                channels,
                {"0201"},
                now,
            )

        self.assertEqual(errors, {})
        self.assertEqual(set(documents), {"epgshare:cl"})
        result = ET.fromstring(documents["epgshare:cl"])
        self.assertEqual(
            {programme.get("channel") for programme in result.findall("programme")},
            {"Canal.24.Horas.(Chile).cl"},
        )
        self.assertEqual(len(result.findall("programme")), 6)

    def test_epgshare_fallback_never_overrides_an_official_channel(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        channels = [
            update_m3u.Channel(
                name="TVN",
                url="https://example.invalid/tvn.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="0104",
            ),
            update_m3u.Channel(
                name="24 Horas",
                url="https://example.invalid/24h.m3u8",
                url_line=2,
                info_line=1,
                tvg_id="0201",
            ),
        ]
        official_root = ET.fromstring(
            self._xmltv_for_source_channel(
                "0104",
                now,
                "TVN oficial",
            )
        )
        fallback_root = ET.fromstring(
            self._xmltv_for_source_channel(
                "Canal.24.Horas.(Chile).cl",
                now,
                "24 Horas EPGShare",
            )
        )
        for index in range(6):
            start = now - timedelta(hours=1) + timedelta(hours=6 * index)
            stop = start + timedelta(hours=6)
            programme = ET.SubElement(
                fallback_root,
                "programme",
                {
                    "start": update_m3u.xmltv_format(start),
                    "stop": update_m3u.xmltv_format(stop),
                    "channel": "Canal.TVN.(Chile).cl",
                },
            )
            ET.SubElement(programme, "title").text = f"TVN EPGShare {index}"
        output, status = update_m3u.build_epg(
            {
                update_m3u.TVN_OFFICIAL_EPG_SOURCE: ET.tostring(
                    official_root,
                    encoding="utf-8",
                    xml_declaration=True,
                ),
                "epgshare:cl": ET.tostring(
                    fallback_root,
                    encoding="utf-8",
                    xml_declaration=True,
                ),
            },
            channels,
            {},
            now=now,
        )

        self.assertEqual(
            status["guide_sources"]["0104"],
            update_m3u.TVN_OFFICIAL_EPG_SOURCE,
        )
        self.assertEqual(status["guide_sources"]["0201"], "epgshare:cl")
        rendered = ET.tostring(ET.fromstring(output)).decode("utf-8")
        self.assertIn("TVN oficial", rendered)
        self.assertNotIn("TVN EPGShare", rendered)
        self.assertIn("24 Horas EPGShare", rendered)

    def test_sky_f1_uhd_reuses_the_sky_hd_guide(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        channels = [
            update_m3u.Channel(
                name="Sky Sports F1",
                url="https://example.invalid/f1.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="SkySportsF1.uk",
            ),
            update_m3u.Channel(
                name="Sky Sports F1 UHD",
                url="https://example.invalid/f1-uhd.m3u8",
                url_line=2,
                info_line=1,
                tvg_id="HighflyPremium.now-sky-sports-f1-2",
            ),
        ]
        output, status = update_m3u.build_epg(
            {
                "epgshare:uk1": self._xmltv_for_source_channel(
                    "SkySp.F1.HD.uk",
                    now,
                    "Sky F1 HD guide",
                )
            },
            channels,
            {},
            now=now,
        )

        self.assertEqual(
            status["guide_sources"]["SkySportsF1.uk"],
            "epgshare:uk1",
        )
        self.assertEqual(
            status["guide_sources"]["HighflyPremium.now-sky-sports-f1-2"],
            "mirror:SkySportsF1.uk",
        )
        rendered = ET.fromstring(output)
        titles_by_channel = {
            channel_id: [
                programme.findtext("title")
                for programme in rendered.findall("programme")
                if programme.get("channel") == channel_id
            ]
            for channel_id in (
                "SkySportsF1.uk",
                "HighflyPremium.now-sky-sports-f1-2",
            )
        }
        self.assertEqual(
            titles_by_channel["SkySportsF1.uk"],
            titles_by_channel["HighflyPremium.now-sky-sports-f1-2"],
        )
        self.assertEqual(
            update_m3u.EPG_PROGRAMME_SOURCES[
                "HighflyPremium.4k-sky-sports-main-events"
            ],
            ("uk1", "SkySpMainEvHD.uk"),
        )

    def test_telehit_official_graphql_requires_current_and_future_window(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        channels = [
            update_m3u.Channel(
                name="Telehit Música",
                url="https://example.invalid/telehit.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="TelehitMusica.mx@SD",
            )
        ]

        def fake_fetch(url, headers, **kwargs):
            self.assertEqual(headers["Referer"], update_m3u.TELEHIT_OFFICIAL_PROGRAMMING_PAGE)
            self.assertEqual(headers["Origin"], "https://www.telehit.com")
            self.assertEqual(kwargs["timeout"], 45)
            shows = [
                {
                    "title": f"Telehit {index}",
                    "description": "Programación oficial de Telehit",
                    "duration": "10800",
                    "schedule": f"{index * 3:02d}:00:00",
                }
                for index in range(8)
            ]
            body = json.dumps(
                {"data": {"getTvShows": {"shows": shows}}}
            ).encode("utf-8")
            return 200, body, url

        with patch.object(update_m3u, "fetch_bytes", side_effect=fake_fetch):
            data, error = update_m3u.fetch_telehit_official_epg(channels, now)

        self.assertIsNone(error)
        self.assertIsNotNone(data)
        result = ET.fromstring(data)
        programmes = result.findall("programme")
        self.assertGreaterEqual(len(programmes), 5)
        self.assertTrue(
            all(
                programme.get("channel") == "TelehitMusica.mx@SD"
                for programme in programmes
            )
        )

    def test_telehit_official_rejects_a_short_or_stale_widget_response(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        channels = [
            update_m3u.Channel(
                name="Telehit Música",
                url="https://example.invalid/telehit.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="TelehitMusica.mx@SD",
            )
        ]

        def fake_fetch(url, headers, **kwargs):
            shows = [
                {
                    "title": f"Telehit corto {index}",
                    "duration": "1800",
                    "schedule": f"{index:02d}:00:00",
                }
                for index in range(3)
            ]
            body = json.dumps(
                {"data": {"getTvShows": {"shows": shows}}}
            ).encode("utf-8")
            return 200, body, url

        with patch.object(update_m3u, "fetch_bytes", side_effect=fake_fetch):
            data, error = update_m3u.fetch_telehit_official_epg(channels, now)

        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertIn("vigente", error)

    def test_telehit_passport_fallback_parses_exact_station_cards(self):
        now = datetime(2026, 9, 9, 15, tzinfo=timezone.utc)
        channels = [
            update_m3u.Channel(
                name="Telehit Música",
                url="https://example.invalid/telehit.m3u8",
                url_line=1,
                info_line=0,
                tvg_id="TelehitMusica.mx@SD",
            )
        ]
        requested_urls = []

        def fake_fetch(url, headers, **kwargs):
            requested_urls.append(url)
            schedule_date = datetime.strptime(
                url.rsplit("/", 1)[-1], "%Y-%m-%d"
            )
            cards = []
            for index in range(26):
                start = schedule_date.replace(hour=6) + timedelta(hours=index)
                cards.append(
                    "<div class=\"list-group-item\" "
                    "data-callsign=\"THIT\" "
                    f"data-st=\"{start:%Y-%m-%d %H:%M:%S}\" "
                    "data-duration=\"60\" "
                    f"data-showName=\"Passport {index}\" "
                    "data-description=\"Guía &amp; Telehit\"></div>"
                )
            return 200, ("<html>" + "".join(cards) + "</html>").encode(), url

        with patch.object(update_m3u, "fetch_bytes", side_effect=fake_fetch):
            data, error = update_m3u.fetch_telehit_passport_epg(channels, now)

        self.assertIsNone(error)
        self.assertIsNotNone(data)
        self.assertEqual(len(requested_urls), 3)
        self.assertTrue(
            all(
                url.startswith(update_m3u.TELEHIT_PASSPORT_STATION_URL + "/")
                for url in requested_urls
            )
        )
        result = ET.fromstring(data)
        programmes = result.findall("programme")
        self.assertGreaterEqual(len(programmes), 20)
        self.assertTrue(
            all(
                programme.get("channel") == "TelehitMusica.mx@SD"
                for programme in programmes
            )
        )
        self.assertEqual(
            programmes[0].findtext("desc"),
            "Guía & Telehit",
        )

    def test_telehit_official_guide_precedes_passport(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        channel = update_m3u.Channel(
            name="Telehit Música",
            url="https://example.invalid/telehit.m3u8",
            url_line=1,
            info_line=0,
            tvg_id="TelehitMusica.mx@SD",
        )
        output, status = update_m3u.build_epg(
            {
                update_m3u.TELEHIT_OFFICIAL_EPG_SOURCE: self._xmltv_for_source_channel(
                    update_m3u.TELEHIT_OFFICIAL_CHANNEL_ID,
                    now,
                    "Telehit oficial",
                ),
                update_m3u.TELEHIT_PASSPORT_EPG_SOURCE: self._xmltv_for_source_channel(
                    update_m3u.TELEHIT_OFFICIAL_CHANNEL_ID,
                    now,
                    "Telehit Passport",
                ),
            },
            [channel],
            {},
            now=now,
        )

        rendered = ET.tostring(ET.fromstring(output)).decode("utf-8")
        self.assertEqual(
            status["guide_sources"][update_m3u.TELEHIT_OFFICIAL_CHANNEL_ID],
            update_m3u.TELEHIT_OFFICIAL_EPG_SOURCE,
        )
        self.assertIn("Telehit oficial", rendered)
        self.assertNotIn("Telehit Passport", rendered)

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

    def test_historical_live_fallback_runs_only_after_current_sources(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        channel = update_m3u.Channel(
            name="Meganoticias",
            url="https://example.invalid/meganoticias.m3u8",
            url_line=1,
            info_line=0,
            tvg_id="Meganoticias.cl",
        )
        historical_root = self._xmltv_for_source_channel(
            "LCH7159",
            now,
            "Meganoticias historico en vivo",
        )

        with TemporaryDirectory() as temporary:
            epg_path = Path(temporary) / "epg.xml"
            with patch.object(update_m3u, "EPG_PATH", epg_path), patch.object(
                update_m3u,
                "fetch_list1_official_epg",
                return_value=({}, {}, set(), {}),
            ), patch.object(
                update_m3u,
                "fetch_epgshare_fallback_epg",
                return_value=({}, {}),
            ), patch.object(
                update_m3u,
                "fetch_tecnocentro_epg",
                return_value=(historical_root, {}),
            ) as tecnocentro_fetch, patch.object(
                update_m3u,
                "fetch_zapping_epg",
                side_effect=AssertionError(
                    "Zapping no debe reemplazar TecnoCentro"
                ),
            ):
                status = update_m3u.refresh_epg_from_official(
                    [channel],
                    now=now,
                    existing_status=None,
                    existing_data=None,
                )
            output = epg_path.read_bytes().decode("utf-8")

        self.assertTrue(tecnocentro_fetch.called)
        self.assertEqual(
            status["historical_fallback_channel_ids"],
            ["Meganoticias.cl"],
        )
        self.assertEqual(
            status["guide_sources"]["Meganoticias.cl"],
            "tecnocentro",
        )
        self.assertIn("Meganoticias historico en vivo", output)
        self.assertIn("fallback historico", output)

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
