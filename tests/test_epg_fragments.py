"""Guía por canal (2026-10-12): fragmentos, unión sin red, correcciones y despachador."""
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epg_dispatch  # noqa: E402
import epg_fragments  # noqa: E402
import update_m3u  # noqa: E402

NOW = datetime(2026, 10, 12, 18, tzinfo=timezone.utc)


def xmltv(moment: datetime) -> str:
    return moment.astimezone(timezone(timedelta(hours=-3))).strftime("%Y%m%d%H%M%S -0300")


def guide(channels: dict[str, list[tuple[int, int, str]]], source: str = "oficial") -> bytes:
    root = ET.Element("tv", {"generator-info-name": "prueba"})
    for channel_id in channels:
        ET.SubElement(root, "channel", {"id": channel_id, "data-guide-source": source})
    for channel_id, items in channels.items():
        for start, stop, title in items:
            programme = ET.SubElement(root, "programme", {
                "start": xmltv(NOW + timedelta(hours=start)),
                "stop": xmltv(NOW + timedelta(hours=stop)),
                "channel": channel_id,
            })
            ET.SubElement(programme, "title").text = title
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def programmes(data: bytes, channel_id: str) -> list[tuple[str, str, str]]:
    root = ET.fromstring(data)
    return [
        (item.findtext("title"), item.get("start"), item.get("stop"))
        for item in root.findall("programme")
        if item.get("channel") == channel_id
    ]


class FragmentTest(unittest.TestCase):
    def test_split_and_assemble_round_trip_keeps_every_programme(self):
        data = guide({"a": [(0, 2, "A1"), (2, 4, "A2")], "b": [(0, 6, "B1")]})
        fragments = epg_fragments.split_epg(data)
        self.assertEqual({"a", "b"}, set(fragments))
        assembled, missing = epg_fragments.assemble(
            fragments, {}, ["a", "b", "c"], root_attributes={"generator-info-name": "x"},
            now=NOW, past_retention=timedelta(hours=6))
        self.assertEqual(["c"], missing)
        self.assertEqual(programmes(data, "a"), programmes(assembled, "a"))
        self.assertEqual(programmes(data, "b"), programmes(assembled, "b"))
        root = ET.fromstring(assembled)
        self.assertEqual(["a", "b"], [c.get("id") for c in root.findall("channel")])
        # XMLTV: todos los <channel> antes de los <programme>.
        tags = [child.tag for child in root]
        self.assertEqual(tags, sorted(tags, key=lambda tag: tag != "channel"))

    def test_app_aliases_are_not_stored_as_fragments(self):
        data = guide({"a": [(0, 2, "A1")]})
        root = ET.fromstring(data)
        ET.SubElement(root, "channel", {"id": "alias", "data-app-alias-of": "a"})
        self.assertEqual({"a"}, set(epg_fragments.split_epg(ET.tostring(root))))

    def test_manual_programme_replaces_only_its_time_range(self):
        fragments = epg_fragments.split_epg(guide({"a": [(0, 4, "Auto")]}))
        manual = guide({"a": [(1, 2, "Manual")]})
        assembled, _ = epg_fragments.assemble(
            fragments, {"a": manual}, ["a"], root_attributes={}, now=NOW,
            past_retention=timedelta(hours=6))
        titles = [title for title, _start, _stop in programmes(assembled, "a")]
        self.assertEqual(["Auto", "Manual", "Auto"], titles)
        spans = [(start, stop) for _title, start, stop in programmes(assembled, "a")]
        self.assertEqual(xmltv(NOW + timedelta(hours=1)), spans[0][1])
        self.assertEqual(xmltv(NOW + timedelta(hours=2)), spans[2][0])
        channel = ET.fromstring(assembled).find("channel")
        self.assertEqual("true", channel.get("data-manual"))

    def test_broken_manual_is_ignored_for_that_channel_only(self):
        fragments = epg_fragments.split_epg(guide({"a": [(0, 4, "A")], "b": [(0, 4, "B")]}))
        assembled, missing = epg_fragments.assemble(
            fragments, {"a": b"<tv><programme start='x' stop='y'/></tv>"}, ["a", "b"],
            root_attributes={}, now=NOW, past_retention=timedelta(hours=6))
        self.assertEqual([], missing)
        self.assertEqual(["A"], [t for t, _, _ in programmes(assembled, "a")])
        self.assertEqual(["B"], [t for t, _, _ in programmes(assembled, "b")])

    def test_unreadable_fragment_only_drops_that_channel(self):
        fragments = epg_fragments.split_epg(guide({"b": [(0, 4, "B")]}))
        fragments["a"] = b"<tv"
        assembled, missing = epg_fragments.assemble(
            fragments, {}, ["a", "b"], root_attributes={}, now=NOW,
            past_retention=timedelta(hours=6))
        self.assertEqual(["a"], missing)
        self.assertEqual(["B"], [t for t, _, _ in programmes(assembled, "b")])

    def test_past_programmes_are_trimmed_at_assembly(self):
        fragments = epg_fragments.split_epg(guide({"a": [(-12, -8, "Viejo"), (0, 2, "Hoy")]}))
        assembled, _ = epg_fragments.assemble(fragments, {}, ["a"], root_attributes={}, now=NOW,
                                              past_retention=timedelta(hours=6))
        self.assertEqual(["Hoy"], [t for t, _, _ in programmes(assembled, "a")])

    def test_failed_source_keeps_the_last_real_guide(self):
        old = epg_fragments.split_epg(guide({"a": [(0, 20, "Real")]}))["a"]
        filler = epg_fragments.split_epg(guide({"a": [(0, 20, "Programación por confirmar")]},
                                               source="pendiente"))["a"]
        fresh = epg_fragments.split_epg(guide({"a": [(0, 30, "Nuevo")]}))["a"]
        titles = frozenset({"programación por confirmar"})
        self.assertFalse(epg_fragments.should_replace(old, filler, NOW, titles))
        self.assertTrue(epg_fragments.should_replace(old, fresh, NOW, titles))
        self.assertTrue(epg_fragments.should_replace(None, filler, NOW, titles))

    def test_filenames_are_safe_and_reversible(self):
        for channel_id in ["0104", "Nauta.52bb@Nauta", "Vavoo.es.ESPN2@TvVoo", "a/b:c"]:
            name = epg_fragments.fragment_filename(channel_id)
            self.assertNotIn("/", name)
            self.assertNotIn(":", name)
            self.assertEqual(channel_id, epg_fragments.channel_id_from_filename(name))


class DispatcherTest(unittest.TestCase):
    def test_each_part_keeps_its_own_rhythm_and_backs_off_on_failure(self):
        state = {"schema": 1, "parts": {}}
        parts = ["tvn-oficial", "red-bull"]
        self.assertEqual(parts, epg_dispatch.due_parts(state, parts, NOW))
        state = epg_dispatch.record(state, parts, {"tvn-oficial": True, "red-bull": False}, NOW)
        self.assertEqual([], epg_dispatch.due_parts(state, parts, NOW + timedelta(minutes=10)))
        # Red Bull falló: vuelve a los 30 min; TVN, recién a las 6 h.
        self.assertEqual(["red-bull"], epg_dispatch.due_parts(state, parts, NOW + timedelta(minutes=31)))
        state = epg_dispatch.record(state, ["red-bull"], {"red-bull": False}, NOW + timedelta(minutes=31))
        self.assertEqual("2026-10-12T19:31:00Z", state["parts"]["red-bull"]["nextDue"])
        self.assertEqual(["tvn-oficial", "red-bull"],
                         epg_dispatch.due_parts(state, parts, NOW + timedelta(hours=6)))

    def test_forced_and_needed_parts(self):
        state = epg_dispatch.record({"schema": 1, "parts": {}}, ["a", "b"], {"a": True, "b": True}, NOW)
        later = NOW + timedelta(minutes=40)
        self.assertEqual(["a"], epg_dispatch.due_parts(state, ["a", "b"], later, forced={"a"}))
        self.assertEqual(["b"], epg_dispatch.due_parts(state, ["a", "b"], later, needed={"b"}))
        self.assertEqual([], epg_dispatch.due_parts(state, ["a", "b"], NOW + timedelta(minutes=5),
                                                    needed={"b"}))

    def test_short_guides_leave_a_notice_and_renew_before_running_out(self):
        index = {"channels": [
            {"id": "corto", "name": "Corto", "lastStop": "2026-10-12T19:30:00Z"},
            {"id": "medio", "name": "Medio", "lastStop": "2026-10-12T22:00:00Z"},
            {"id": "largo", "name": "Largo", "lastStop": "2026-10-13T18:00:00Z"},
            {"id": "vacio", "name": "Vacío", "lastStop": None},
            {"id": "live", "name": "Rewind", "lastStop": None},
        ]}
        notices = epg_dispatch.build_notices(epg_dispatch.channel_horizons(index, NOW, {"live"}))
        self.assertEqual({"corto", "medio", "vacio"}, set(notices))
        self.assertEqual(1.5, notices["corto"]["hours"])
        self.assertEqual("vigilar", notices["medio"]["action"])
        self.assertEqual({"corto", "vacio"}, epg_dispatch.urgent_channels(notices))

    def test_tvn3_uses_claro_schedule_after_zapping(self):
        self.assertEqual(
            [("zapping-guia-publica", "1437"), ("claro-sinopsis", "sinopsis:1437")],
            update_m3u.epg_source_chain("1437")[:2])
        self.assertEqual({"zapping-guia-publica", "claro-sinopsis"}, update_m3u.epg_channel_parts("1437"))
        self.assertNotIn("1437", update_m3u.EPG_ALLOWED_EMPTY_IDS)

    def test_etc_tv_uses_claro_schedule_without_zapping(self):
        # ETC TV (2026-10-18): Claro es la fuente principal, verificada con
        # fotogramas del stream. Zapping queda fuera: su guía para este id no
        # coincide con la señal (se comprobó contra el propio canal en vivo).
        etc_id = "PublicDirect.3ba5922c6040fadb816835b1"
        self.assertEqual(
            [("claro-sinopsis", "sinopsis:" + etc_id)],
            update_m3u.epg_source_chain(etc_id)[:1])
        self.assertEqual({"claro-sinopsis"}, update_m3u.epg_channel_parts(etc_id))
        self.assertNotIn(etc_id, update_m3u.ZAPPING_EPG_CHANNELS)

    def test_backoff_never_exceeds_the_normal_rhythm(self):
        self.assertEqual(timedelta(hours=2), epg_dispatch.retry_after("red-bull", 9))
        self.assertEqual(timedelta(hours=6), epg_dispatch.retry_after("tvn-oficial", 9))
        self.assertEqual(timedelta(minutes=30), epg_dispatch.retry_after("tvn-oficial", 1))


class RunnerIntegrationTest(unittest.TestCase):
    def test_every_channel_maps_to_known_parts(self):
        names = set(update_m3u.epg_part_names())
        self.assertIn("tvn-oficial", update_m3u.epg_channel_parts("0104"))
        self.assertEqual({"red-bull"}, update_m3u.epg_channel_parts(update_m3u.RED_BULL_CHILE_ID))
        for channel_id in ["0104", "0105", "0106", "0107", "0102", "XITEJustChill.nl"]:
            self.assertTrue(update_m3u.epg_channel_parts(channel_id) <= names, channel_id)

    def test_one_broken_channel_does_not_break_the_build(self):
        good = update_m3u.Channel(name="Bueno", url="https://e.invalid/a.m3u8", info_line=0,
                                  url_line=1, tvg_id="bueno.cl", display_name="Bueno")
        bad = update_m3u.Channel(name="Malo", url="https://e.invalid/b.m3u8", info_line=0,
                                 url_line=1, tvg_id="malo.cl", display_name="Malo")
        source = guide({"src-bueno": [(0, 30, "Programa")], "src-malo": [(0, 30, "Otro")]})
        original = update_m3u.epg_source_chain

        def chain(target_id):
            if target_id == "malo.cl":
                raise RuntimeError("cadena rota")
            return [("fuente", "src-bueno")] if target_id == "bueno.cl" else original(target_id)

        with patch.object(update_m3u, "epg_source_chain", chain):
            output, _status = update_m3u.build_epg({"fuente": source}, [good, bad], {}, now=NOW)
        self.assertIn("Programa", [t for t, _, _ in programmes(output, "bueno.cl")])
        self.assertNotIn("Otro", [t for t, _, _ in programmes(output, "malo.cl")])

    def test_assembly_respects_scope_and_rebuilds_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            fragments_dir = base / "canales"
            for channel_id, fragment in epg_fragments.split_epg(
                    guide({"a": [(0, 30, "A")], "fuera": [(0, 30, "X")]})).items():
                epg_fragments.write_fragment(fragments_dir, channel_id, fragment)
            output = base / "epg.xml"
            with patch.object(update_m3u, "EPG_FRAGMENTS_DIR", fragments_dir), \
                    patch.object(update_m3u, "EPG_MANUAL_DIR", base / "manual"), \
                    patch.object(update_m3u, "EPG_ROOT_META_PATH", base / "raiz.json"), \
                    patch.object(update_m3u, "epg_scope_order", lambda: (["a", "nuevo"], {"a"})), \
                    patch.object(update_m3u, "add_app_epg_aliases", lambda data: data):
                status = update_m3u.assemble_epg_from_fragments(output_path=output, now=NOW)
            root = ET.fromstring(output.read_bytes())
        self.assertEqual(["a"], [c.get("id") for c in root.findall("channel")])
        self.assertEqual(["nuevo"], status["missing_fragments"])
        self.assertEqual("m3u.m3u", root.get("data-epg-scope"))
        self.assertEqual("lista-m3u updater", root.get("generator-info-name"))


    def test_index_links_editor_rows_to_guide_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_path = Path(temporary) / "indice.json"
            data = guide({"0104": [(0, 30, "TVN")], "X@TvVoo": [(0, 30, "Sky")]})
            with patch.object(update_m3u, "EPG_INDEX_PATH", index_path),                     patch.object(update_m3u, "epg_editor_keys",
                                 lambda ids: {"0104": ["m3u:0104"],
                                              "X@TvVoo": ["m3u:X@TvVoo", "provider:tvvoo:clave"]}):
                update_m3u.write_epg_index(data, ["0104", "X@TvVoo"], NOW)
            index = json.loads(index_path.read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry for entry in index["channels"]}
        self.assertEqual("0104.xml", by_id["0104"]["file"])
        self.assertIn("provider:tvvoo:clave", by_id["X@TvVoo"]["keys"])
        self.assertEqual("2026-10-14T00:00:00Z", by_id["0104"]["lastStop"])

if __name__ == "__main__":
    unittest.main()
