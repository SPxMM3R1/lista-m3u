import json
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
        root = ET.fromstring(source)
        programmes = root.findall("programme")
        self.assertEqual(len(programmes), 3)
        self.assertEqual(
            [programme.findtext("title") for programme in programmes],
            ["Siempre lunes", "¿Dónde está Elisa?", "Legado: tierra adentro"],
        )
        self.assertEqual({item.get("channel") for item in programmes}, {"1437"})

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


if __name__ == "__main__":
    unittest.main()
