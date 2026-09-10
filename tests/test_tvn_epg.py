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
    def test_chv_parser_extracts_official_weekly_cards(self) -> None:
        days = []
        for index, day_name in enumerate(
            ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        ):
            days.append(
                f'''
                <div class="schedule-section__list" data-day="{day_name}">
                  <article class="schedule-card">
                    <div class="schedule-card__hour">09:30</div>
                    <strong class="schedule-card__title"><a>NOTICIAS {day_name}</a></strong>
                  </article>
                </div>
                '''
            )

        schedules = update_m3u.chv_schedule_items("\n".join(days))

        self.assertEqual(7, len(schedules))
        self.assertEqual("NOTICIAS lunes", schedules[0][0][1])
        self.assertEqual("09:30", schedules[3][0][0].strftime("%H:%M"))

    def test_official_chv_schedule_overrides_aggregated_schedule(self) -> None:
        now = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
        html = "".join(
            f'''
            <div class="schedule-section__list">
              <article class="schedule-card">
                <div class="schedule-card__hour">{hour:02d}:00</div>
                <div class="schedule-card__title"><a>PROGRAMA OFICIAL {index}</a></div>
              </article>
            </div>
            '''
            for index, hour in enumerate((9, 10, 11, 12, 13, 14, 15))
        )
        with patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(200, html.encode("utf-8"), update_m3u.CHV_PROGRAMMING_PAGE),
        ):
            official, error = update_m3u.fetch_chv_official_epg(
                [channel("CHV", "0106")], now
            )

        self.assertIsNone(error)
        self.assertIsNotNone(official)
        aggregated = ET.Element("tv")
        bad = ET.SubElement(
            aggregated,
            "programme",
            {
                "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                "channel": "0106",
            },
        )
        ET.SubElement(bad, "title").text = "AGREGADA INCORRECTA"

        output, status = update_m3u.build_epg(
            {
                "cl": ET.tostring(aggregated, encoding="utf-8"),
                update_m3u.ZAPPING_EPG_SOURCE: ET.tostring(
                    aggregated, encoding="utf-8"
                ),
                update_m3u.CHV_OFFICIAL_EPG_SOURCE: official,
            },
            [channel("CHV", "0106")],
            {},
            now=now,
        )
        root = ET.fromstring(output)
        titles = [
            item.findtext("title", "")
            for item in root.findall("./programme[@channel='0106']")
        ]
        self.assertIn("Programa Oficial 3", titles)
        self.assertNotIn("AGREGADA INCORRECTA", titles)
        self.assertEqual(
            update_m3u.CHV_OFFICIAL_EPG_SOURCE,
            root.find("./channel[@id='0106']").get("data-guide-source"),
        )
        self.assertGreater(status["programmes"], 0)

    def test_dw_english_parser_and_official_source_use_english_schedule(self) -> None:
        now = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
        records = []
        for index in range(5):
            start = now + timedelta(hours=index)
            stop = start + timedelta(hours=1)
            records.append(
                "{"
                f'"startDate":"{start.strftime("%Y-%m-%dT%H:%M:%SZ")}",'
                f'"endDate":"{stop.strftime("%Y-%m-%dT%H:%M:%SZ")}",'
                '"program":{"name":"DW NEWS"},'
                f'"programElement":{{"name":"WORLD UPDATE {index}"}}'
                "}"
            )
        html = "<script>" + ",".join(records) + "</script>"

        slots = update_m3u.dw_english_schedule_slots(html)
        self.assertEqual(5, len(slots))
        self.assertEqual("DW News: World Update 0", slots[0][2])

        with patch.object(
            update_m3u,
            "fetch_bytes",
            return_value=(
                200,
                html.encode("utf-8"),
                update_m3u.DW_ENGLISH_PROGRAMMING_PAGE,
            ),
        ):
            official, error = update_m3u.fetch_dw_english_official_epg(
                [channel("DW English", "DWEnglish.de")], now
            )

        self.assertIsNone(error)
        self.assertIsNotNone(official)
        root = ET.fromstring(official)
        self.assertEqual(
            "DW News: World Update 0",
            root.find("./programme").findtext("title"),
        )

    def test_dw_english_uses_zapping_dwe_when_official_is_unavailable(self) -> None:
        self.assertEqual("dwe", update_m3u.ZAPPING_EPG_CHANNELS["DWEnglish.de"])
        now = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
        source_root = ET.Element("tv")
        programme = ET.SubElement(
            source_root,
            "programme",
            {
                "start": update_m3u.xmltv_format_chile(now - timedelta(minutes=30)),
                "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=2)),
                "channel": "DWEnglish.de",
            },
        )
        ET.SubElement(programme, "title").text = "DW NEWS ENGLISH"

        output, status = update_m3u.build_epg(
            {update_m3u.ZAPPING_EPG_SOURCE: ET.tostring(source_root, encoding="utf-8")},
            [channel("DW English", "DWEnglish.de")],
            {},
            now=now,
        )

        root = ET.fromstring(output)
        dw_channel = root.find("./channel[@id='DWEnglish.de']")
        self.assertEqual(update_m3u.ZAPPING_EPG_SOURCE, dw_channel.get("data-guide-source"))
        self.assertEqual(
            "DW News English",
            root.find("./programme[@channel='DWEnglish.de']").findtext("title"),
        )
        self.assertGreater(status["programmes"], 0)

    def test_final_epg_titles_are_not_all_uppercase(self) -> None:
        now = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
        source_root = ET.Element("tv")
        programme = ET.SubElement(
            source_root,
            "programme",
            {
                "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                "channel": "0104",
            },
        )
        ET.SubElement(programme, "title").text = "THE DAY NEWS"

        output, _ = update_m3u.build_epg(
            {update_m3u.ZAPPING_EPG_SOURCE: ET.tostring(source_root, encoding="utf-8")},
            [channel("TVN", "0104")],
            {},
            now=now,
        )

        root = ET.fromstring(output)
        self.assertEqual(
            "The Day News",
            root.find("./programme[@channel='0104']").findtext("title"),
        )

    def test_mexico_epgshare_mapping_covers_telehit_and_sony(self) -> None:
        self.assertEqual(
            update_m3u.EPG_SOURCES["mx1"],
            "https://epgshare01.online/epgshare01/epg_ripper_MX1.xml.gz",
        )
        self.assertEqual(
            update_m3u.EPG_PROGRAMME_SOURCES["TelehitMusica.mx@SD"],
            ("mx1", "Canal.Telehit.Música.mx"),
        )
        self.assertEqual(
            update_m3u.EPG_PROGRAMME_SOURCES["SonyChannelAndes.us@SD"],
            ("mx1", "Canal.Sony.(México).mx"),
        )

    def test_epgshare_scope_skips_feeds_without_catalogue_targets(self) -> None:
        sources = update_m3u.epgshare_source_names_for(
            [
                channel("TVN", "0104"),
                channel("La Red", "0102"),
                channel("Telehit Música", "TelehitMusica.mx@SD"),
                channel("Sony Channel", "SonyChannelAndes.us@SD"),
            ]
        )

        self.assertEqual(sources, frozenset({"cl", "mx1"}))
        self.assertNotIn("au1", update_m3u.EPG_SOURCES)
        self.assertNotIn("sg1", update_m3u.EPG_SOURCES)
        self.assertNotIn("ng1", update_m3u.EPG_SOURCES)

    def test_mexico_epgshare_mapping_produces_named_programmes(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        source_root = ET.Element("tv")
        for source_id, title in (
            ("Canal.Telehit.Música.mx", "Top 10"),
            ("Canal.Sony.(México).mx", "Búsqueda implacable"),
        ):
            ET.SubElement(source_root, "channel", {"id": source_id})
            programme = ET.SubElement(
                source_root,
                "programme",
                {
                    "start": update_m3u.xmltv_format_chile(
                        now - timedelta(hours=1)
                    ),
                    "stop": update_m3u.xmltv_format_chile(
                        now + timedelta(hours=25)
                    ),
                    "channel": source_id,
                },
            )
            ET.SubElement(programme, "title").text = title

        output, status = update_m3u.build_epg(
            {"mx1": ET.tostring(source_root, encoding="utf-8")},
            [
                channel("Telehit Música", "TelehitMusica.mx@SD"),
                channel("Sony Channel", "SonyChannelAndes.us@SD"),
            ],
            {},
            now=now,
        )

        root = ET.fromstring(output)
        self.assertEqual(
            root.find("./programme[@channel='TelehitMusica.mx@SD']").findtext(
                "title"
            ),
            "Top 10",
        )
        self.assertEqual(
            root.find("./programme[@channel='SonyChannelAndes.us@SD']").findtext(
                "title"
            ),
            "Búsqueda implacable",
        )
        self.assertEqual(
            status["guide_sources"]["TelehitMusica.mx@SD"],
            "mx1",
        )
        self.assertEqual(
            status["guide_sources"]["SonyChannelAndes.us@SD"],
            "mx1",
        )

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
        self.assertEqual(
            {item.findtext("title") for item in programmes},
            {"Live"},
        )
        self.assertTrue(all(item.get("start", "")[8:14] == "000000" for item in programmes))
        self.assertTrue(all(item.get("stop", "")[8:14] == "235900" for item in programmes))
        self.assertFalse(any(item.find("desc") is not None for item in programmes))
        self.assertEqual(status["programmes"], len(programmes))

    def test_13go_uses_diego_y_glot_for_real_and_continuity_blocks(self) -> None:
        now = datetime(2026, 8, 28, 18, tzinfo=timezone.utc)
        source = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="13kids"><display-name>13 Go</display-name></channel>
  <programme start="20260828170000 +0000" stop="20260828190000 +0000" channel="13kids">
    <title lang="es">Programa que no debe mostrarse</title>
    <sub-title lang="es">Episodio temporal</sub-title>
  </programme>
</tv>
"""

        output, status = update_m3u.build_epg(
            {update_m3u.CANAL13_13GO_EPG_SOURCE: source},
            [channel("13 Go", "13Kids.cl")],
            {},
            now=now,
        )

        root = ET.fromstring(output)
        channel_element = root.find("./channel[@id='13Kids.cl']")
        self.assertEqual(
            channel_element.get("data-guide"),
            "parrilla Diego y Glot + continuidad",
        )
        programmes = root.findall("./programme[@channel='13Kids.cl']")
        self.assertGreater(len(programmes), 1)
        self.assertEqual(
            {item.findtext("title") for item in programmes}, {"Diego y Glot"}
        )
        self.assertFalse(any(item.find("sub-title") is not None for item in programmes))
        self.assertEqual(status["programmes"], len(root.findall("programme")))

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
        retired = channel("Canal retirado", "retired.channel")
        stale = channel("Canal antiguo", "stale.channel")

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            epg_path = temporary / "epg.xml"
            public_playlist = temporary / "m3u.m3u"
            root = ET.Element(
                "tv",
                {"data-generated-at": (now - timedelta(hours=1)).isoformat()},
            )
            for item in (active, retired, stale):
                ET.SubElement(root, "channel", {"id": item.tvg_id})
                programme = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": update_m3u.xmltv_format_chile(
                            now - timedelta(hours=1)
                        ),
                        "stop": update_m3u.xmltv_format_chile(
                            now + timedelta(hours=25)
                        ),
                        "channel": item.tvg_id,
                    },
                )
                ET.SubElement(programme, "title").text = f"Programa {item.name}"
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
                status = update_m3u.refresh_epg([active, retired])

        self.assertTrue(status["reused"])
        self.assertEqual(status["channels"], 2)

    def test_main_playlist_epg_gate_requires_every_principal_channel(self) -> None:
        now = datetime(2026, 8, 29, 12, tzinfo=timezone.utc)
        principal = [channel("TVN", "0104"), channel("Meganoticias", "Meganoticias.cl")]

        root = ET.Element("tv", {"data-generated-at": now.isoformat()})
        for item in principal:
            ET.SubElement(
                root,
                "channel",
                {"id": item.tvg_id, "data-guide": "parrilla oficial"},
            )
            programme = ET.SubElement(
                root,
                "programme",
                {
                    "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                    "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                    "channel": item.tvg_id,
                },
            )
            ET.SubElement(programme, "title").text = f"Programa {item.name}"
        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        status = update_m3u.validate_main_playlist_epg(principal, data=data, now=now)

        self.assertTrue(status["ok"])
        self.assertEqual(status["required_channels"], 2)
        self.assertEqual(status["coverage_percent"], 100)

        incomplete = update_m3u.validate_main_playlist_epg(
            principal[:1], data=data, now=now
        )
        self.assertTrue(incomplete["ok"])

        missing = ET.Element("tv")
        ET.SubElement(missing, "channel", {"id": "0104"})
        missing_programme = ET.SubElement(
            missing,
            "programme",
            {
                "start": update_m3u.xmltv_format_chile(now - timedelta(hours=1)),
                "stop": update_m3u.xmltv_format_chile(now + timedelta(hours=25)),
                "channel": "0104",
            },
        )
        ET.SubElement(missing_programme, "title").text = "TVN"
        failed = update_m3u.validate_main_playlist_epg(
            principal, data=ET.tostring(missing, encoding="utf-8"), now=now
        )
        self.assertFalse(failed["ok"])
        self.assertIn("Meganoticias.cl", failed["error"])


if __name__ == "__main__":
    unittest.main()
