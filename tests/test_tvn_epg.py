import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import update_m3u


def channel(name: str, tvg_id: str) -> update_m3u.Channel:
    return update_m3u.Channel(
        name=name,
        url="https://example.invalid/live.m3u8",
        url_line=0,
        tvg_id=tvg_id,
        display_name=name,
    )


class TvnEpgTests(unittest.TestCase):
    def test_tvn3_survives_failure_from_another_zapping_page(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        channels = [channel("TVN3", "1437"), channel("Mega", "0105")]
        tvn3_rows = [
            (now - timedelta(hours=1), "Pasiones"),
            (now + timedelta(hours=11), "Calle 7"),
            (now + timedelta(hours=23), "Siempre lunes"),
            (now + timedelta(hours=35), "El dia menos pensado"),
        ]

        def fake_fetch(url, *_args, **_kwargs):
            if url == update_m3u.ZAPPING_NOWPLAYING_URL:
                return 200, b'{"data":{"schedule":{}}}', url
            if url.endswith("/tvn3/"):
                return 200, b"tvn3", url
            raise TimeoutError("fallo simulado independiente")

        def fake_rows(page_html: str):
            return tvn3_rows if page_html == "tvn3" else []

        with patch.object(update_m3u, "fetch_bytes", side_effect=fake_fetch), patch.object(
            update_m3u, "zapping_schedule_rows", side_effect=fake_rows
        ):
            source, errors = update_m3u.fetch_zapping_epg(channels, now)

        self.assertIsNotNone(source)
        self.assertNotIn("1437", errors)
        self.assertIn("0105", errors)
        source_root = ET.fromstring(source)
        self.assertEqual(
            {programme.get("channel") for programme in source_root.findall("programme")},
            {"1437"},
        )

        output, status = update_m3u.build_epg(
            {update_m3u.ZAPPING_EPG_SOURCE: source},
            [channels[0]],
            {},
            now=now,
        )
        output_root = ET.fromstring(output)
        tvn3 = output_root.find("./channel[@id='1437']")
        self.assertIsNotNone(tvn3)
        self.assertEqual(tvn3.findtext("url"), update_m3u.TVN3_OFFICIAL_PAGE)
        self.assertEqual(tvn3.get("data-guide-source"), update_m3u.ZAPPING_EPG_SOURCE)
        self.assertGreater(status["programmes"], 0)

    def test_tvn3_uses_public_nowplaying_when_html_is_geoblocked(self) -> None:
        now = datetime(2026, 8, 28, 18, tzinfo=timezone.utc)
        channels = [channel("TVN3", "1437")]
        cards = [
            {
                "start_time": int((now - timedelta(hours=1)).timestamp()),
                "end_time": int(now.timestamp()),
                "title": "Siempre lunes",
            },
            {
                "start_time": int(now.timestamp()),
                "end_time": int((now + timedelta(hours=1)).timestamp()),
                "title": "¿Dónde está Elisa?",
            },
            {
                "start_time": int((now + timedelta(hours=1)).timestamp()),
                "end_time": int((now + timedelta(hours=2)).timestamp()),
                "title": "Legado: tierra adentro",
            },
        ]
        payload = {
            "data": {
                "schedule": {
                    "tvn3": {
                        "past": [cards[0]],
                        "now": cards[1],
                        "next": [cards[2]],
                    }
                }
            }
        }

        def fake_fetch(url, *_args, **_kwargs):
            raise TimeoutError("Acceso denegado: Pais no permitido")

        curl_result = SimpleNamespace(
            stdout=json.dumps(payload, ensure_ascii=False).encode()
        )
        with patch.object(
            update_m3u, "fetch_bytes", side_effect=fake_fetch
        ), patch.object(
            update_m3u.subprocess, "run", return_value=curl_result
        ) as curl_run:
            source, errors = update_m3u.fetch_zapping_epg(channels, now)

        self.assertIsNotNone(source)
        self.assertEqual(errors, {})
        curl_run.assert_called_once()
        curl_command = curl_run.call_args.args[0]
        self.assertIn("--connect-to", curl_command)
        self.assertIn(
            "charly.zappingtv.com:443:br-apig.zappingtv.com:443",
            curl_command,
        )
        root = ET.fromstring(source)
        programmes = root.findall("programme")
        self.assertEqual(len(programmes), 3)
        self.assertEqual(
            [programme.findtext("title") for programme in programmes],
            ["Siempre lunes", "¿Dónde está Elisa?", "Legado: tierra adentro"],
        )
        self.assertEqual({item.get("channel") for item in programmes}, {"1437"})

        output, status = update_m3u.build_epg(
            {update_m3u.ZAPPING_EPG_SOURCE: source}, channels, {}, now=now
        )
        output_root = ET.fromstring(output)
        tvn3 = output_root.find("./channel[@id='1437']")
        self.assertEqual(
            tvn3.get("data-guide"), "parrilla real parcial + continuidad tecnica"
        )
        self.assertGreater(status["programmes"], 3)
        self.assertNotIn(
            "TVN3",
            [item.findtext("title") for item in output_root.findall("programme")],
        )

    def test_channel_without_real_source_gets_explicit_technical_coverage(self) -> None:
        now = datetime(2026, 8, 28, 18, tzinfo=timezone.utc)
        output, status = update_m3u.build_epg(
            {}, [channel("Canal sin fuente", "unknown.channel")], {}, now=now
        )

        root = ET.fromstring(output)
        entry = root.find("./channel[@id='unknown.channel']")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("data-guide"), "continuidad tecnica")
        self.assertEqual(entry.get("data-guide-source"), "continuidad-tecnica")
        programmes = root.findall("./programme[@channel='unknown.channel']")
        self.assertGreater(len(programmes), 0)
        self.assertIn("programacion no disponible", programmes[0].findtext("title"))
        self.assertEqual(status["programmes"], len(programmes))

    def test_official_tvn_json_never_populates_tvn3(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        channels = [channel("TVN", "0104"), channel("TVN3", "1437")]
        items = []
        for hour in range(8, 14):
            items.append(
                {
                    "senal": 5,
                    "fecha": "28/08/2026",
                    "horaInicio": f"{hour:02d}:00:00",
                    "horaTermino": f"{hour + 1:02d}:00:00",
                    "programa": f"Programa TVN {hour}",
                }
            )
        body = f"jsonp({json.dumps(items)});".encode()

        with patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(200, body, "https://estaticos.tvn.cl/epg/tvn/"),
        ):
            source, error = update_m3u.fetch_tvn_official_epg(channels, now)

        self.assertIsNone(error)
        self.assertIsNotNone(source)
        root = ET.fromstring(source)
        self.assertEqual(
            {programme.get("channel") for programme in root.findall("programme")},
            {"0104"},
        )

    def test_la_red_official_source_overrides_aggregated_schedule(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        la_red = channel("La Red", "0102")

        def source(channel_id: str, title: str) -> bytes:
            root = ET.Element("tv")
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                    "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                    "channel": channel_id,
                },
            )
            ET.SubElement(programme, "title").text = title
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)

        output, status = update_m3u.build_epg(
            {
                "cl": source("Canal.La.Red.(Chile).cl", "EPGShare incorrecta"),
                update_m3u.ZAPPING_EPG_SOURCE: source("0102", "Zapping incorrecta"),
                update_m3u.LA_RED_OFFICIAL_EPG_SOURCE: source(
                    "0102", "La Red oficial"
                ),
            },
            [la_red],
            {},
            now=now,
        )

        root = ET.fromstring(output)
        programme = root.find("./programme[@channel='0102']")
        self.assertEqual(programme.findtext("title"), "La Red oficial")
        la_red_epg = root.find("./channel[@id='0102']")
        self.assertEqual(
            la_red_epg.get("data-guide-source"),
            update_m3u.LA_RED_OFFICIAL_EPG_SOURCE,
        )
        self.assertEqual(status["programmes"], 1)

    def test_epg_overlap_is_reported_without_invalidating_the_whole_guide(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        root = ET.Element("tv")
        ET.SubElement(root, "channel", {"id": "overlap.channel"})
        for start, stop, title in (
            (now - timedelta(hours=1), now + timedelta(hours=2), "Bloque A"),
            (now + timedelta(hours=1), now + timedelta(hours=25), "Bloque B"),
        ):
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format_chile(start),
                    "stop": update_m3u.xmltv_format_chile(stop),
                    "channel": "overlap.channel",
                },
            )
            ET.SubElement(programme, "title").text = title

        status = update_m3u.epg_status_from_xml(
            ET.tostring(root, encoding="utf-8", xml_declaration=True),
            {"overlap.channel"},
            now=now,
            minimum_future=timedelta(hours=24),
        )

        self.assertTrue(status["ok"])
        self.assertIn("overlap.channel", status["warnings"][0])

    def test_la_red_does_not_fallback_to_aggregated_epg(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        la_red = channel("La Red", "0102")

        def source(channel_id: str, title: str) -> bytes:
            root = ET.Element("tv")
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                    "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                    "channel": channel_id,
                },
            )
            ET.SubElement(programme, "title").text = title
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)

        output, status = update_m3u.build_epg(
            {
                "cl": source("Canal.La.Red.(Chile).cl", "EPGShare no autorizada"),
                update_m3u.ZAPPING_EPG_SOURCE: source("0102", "Zapping no autorizada"),
            },
            [la_red],
            {},
            now=now,
        )

        root = ET.fromstring(output)
        titles = [item.findtext("title", "") for item in root.findall("programme")]
        self.assertFalse(any("no autorizada" in title for title in titles))
        la_red_epg = root.find("./channel[@id='0102']")
        self.assertEqual(la_red_epg.get("data-guide-source"), "continuidad-tecnica")
        self.assertGreater(status["programmes"], 0)

    def test_epg_accepts_retired_channels_in_previous_publication(self) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        active = channel("Canal activo", "active.channel")

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            epg_path = temporary / "epg.xml"
            public_playlist = temporary / "m3u.m3u"
            root = ET.Element(
                "tv",
                {"data-generated-at": (now - timedelta(hours=1)).isoformat()},
            )
            ET.SubElement(root, "channel", {"id": active.tvg_id})
            ET.SubElement(root, "channel", {"id": "retired.channel"})
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                    "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                    "channel": active.tvg_id,
                },
            )
            ET.SubElement(programme, "title").text = "Programa vigente"
            epg_path.write_bytes(
                ET.tostring(root, encoding="utf-8", xml_declaration=True)
            )
            public_playlist.write_text(
                "#EXTM3U\n"
                '#EXTINF:-1 tvg-id="active.channel",Canal activo\n'
                "https://example.invalid/live.m3u8\n",
                encoding="utf-8",
            )

            with patch.object(update_m3u, "EPG_PATH", epg_path), patch.object(
                update_m3u, "DEFAULT_PLAYLIST", public_playlist
            ):
                status = update_m3u.refresh_epg([active])

        self.assertTrue(status["reused"])
        self.assertEqual(status["channels"], 1)


if __name__ == "__main__":
    unittest.main()
