import json
import pathlib
import re
import unittest

import update_m3u

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Lista2EpgMapTest(unittest.TestCase):
    """La EPG de Lista 2 solo usa IDs publicados y fuentes conocidas."""

    def test_mapping_covers_the_published_list_and_known_sources(self):
        mapping = update_m3u.load_epg_l2_map()
        self.assertGreaterEqual(len(mapping), 1000)
        lines = (ROOT / "m3u-externa.m3u").read_text(encoding="utf-8").splitlines()
        published = set(re.findall(r'tvg-id="([^"]+)"', "\n".join(lines)))
        # 2026-10-21: el mapa puede conservar canales que después fueron a la papelera; la
        # guía solo se arma para los publicados (ver test de alcance).
        self.assertGreaterEqual(len(set(mapping) & published), 1000)
        for target_id, (source, source_id) in mapping.items():
            with self.subTest(channel=target_id):
                # 2026-10-24: guía Claro por familia (claro:<región>:<group_id>) o EPGShare.
                if source == update_m3u.CLARO_GUIDE_PART:
                    self.assertIsNotNone(update_m3u.claro_guide_key(source_id))
                    self.assertIn(target_id, update_m3u.CLARO_GUIDE_CHANNELS)
                else:
                    self.assertIn(source, update_m3u.EPG_SOURCES)
                self.assertTrue(source_id)

    def test_scope_includes_the_mapped_lista2_channels(self):
        scope, ids = update_m3u.epg_scope_channels()
        mapping = update_m3u.load_epg_l2_map()
        lines = (ROOT / "m3u-externa.m3u").read_text(encoding="utf-8").splitlines()
        published = set(re.findall(r'tvg-id="([^"]+)"', chr(10).join(lines)))
        self.assertTrue((set(mapping) & published).issubset(ids))
        # Lista 2 baja con la papelera desde la app (A3Cine, 2026-10-22): piso como el del mapa.
        self.assertGreaterEqual(len(scope), 1000)


class Lista2ClaroFamilyGuideTest(unittest.TestCase):
    def test_family_copies_share_one_claro_guide_with_epgshare_backup(self):
        mapping = json.loads((ROOT / "epg-l2-map.json").read_text(encoding="utf-8"))["channels"]
        claro = {tid: entry for tid, entry in mapping.items() if entry["source"] == update_m3u.CLARO_GUIDE_PART}
        self.assertGreaterEqual(len(claro), 900)
        # Una guía por familia: muchas copias, pocas claves.
        self.assertLessEqual(len({entry["source_id"] for entry in claro.values()}), 100)
        for target_id, entry in claro.items():
            backup = entry.get("backup")
            if backup:
                with self.subTest(channel=target_id):
                    self.assertIn(backup["source"], update_m3u.EPG_SOURCES)
                    self.assertEqual(
                        (backup["source"], backup["source_id"]),
                        update_m3u.EPGSHARE_BACKUP_CHANNELS[target_id])
                    self.assertEqual(
                        [(update_m3u.CLARO_GUIDE_PART, entry["source_id"]),
                         (backup["source"], backup["source_id"])],
                        update_m3u.epg_source_chain(target_id)[:2])
                break


if __name__ == "__main__":
    unittest.main()
