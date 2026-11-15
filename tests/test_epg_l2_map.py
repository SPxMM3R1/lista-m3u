import json
import pathlib
import re
import unittest

import update_m3u

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Lista2EpgMapTest(unittest.TestCase):
    """La EPG de Lista 2 solo usa IDs publicados y fuentes conocidas."""

    def test_mapping_uses_known_sources(self):
        mapping = update_m3u.load_epg_l2_map()
        # 2026-11-02: los clones de Lista 2 pasaron a backups.json y salieron del mapa (~770).
        # 2026-11-03: tercera ronda de clones: 681.
        # 2026-11-04: clones de Lista 2 a respaldo de Lista 1: 649.
        # 2026-11-07: revisión de Lista 2 (37 clones a respaldo, 27 sin señal a la papelera): 603.
        self.assertGreaterEqual(len(mapping), 590)
        for target_id, (source, source_id) in mapping.items():
            with self.subTest(channel=target_id):
                # 2026-10-24: guía Claro por familia (claro:<región>:<group_id>) o EPGShare.
                if source == update_m3u.CLARO_GUIDE_PART:
                    self.assertIsNotNone(update_m3u.claro_guide_key(source_id))
                    self.assertIn(target_id, update_m3u.CLARO_GUIDE_CHANNELS)
                elif source == update_m3u.GATOTV_PART:
                    self.assertTrue(source_id.startswith(update_m3u.GATOTV_ID_PREFIX))
                    self.assertIn(target_id, update_m3u.GATOTV_CHANNELS)
                else:
                    self.assertIn(source, update_m3u.EPG_SOURCES)
                self.assertTrue(source_id)

    def test_scope_includes_the_mapped_lista2_channels(self):
        scope, ids = update_m3u.epg_scope_channels()
        mapping = update_m3u.load_epg_l2_map()
        lines = (ROOT / "m3u-externa.m3u").read_text(encoding="utf-8").splitlines()
        published = set(re.findall(r'tvg-id="([^"]+)"', chr(10).join(lines)))
        main_ids = {channel.tvg_id for channel in update_m3u.main_playlist_channels()}
        extra_ids = {channel.tvg_id for channel in update_m3u.epg_scope_extra_channels(main_ids)}
        # Las bajas desde la app cambian el tamaño sin romper el contrato.
        expected_ids = main_ids | extra_ids | (set(mapping) & published)
        self.assertEqual(expected_ids, ids)
        self.assertEqual(expected_ids, {channel.tvg_id for channel in scope})
        self.assertEqual(len(expected_ids), len(scope))


class Lista2ClaroFamilyGuideTest(unittest.TestCase):
    def test_family_copies_share_one_claro_guide_with_epgshare_backup(self):
        mapping = json.loads((ROOT / "epg-l2-map.json").read_text(encoding="utf-8"))["channels"]
        claro = {tid: entry for tid, entry in mapping.items() if entry["source"] == update_m3u.CLARO_GUIDE_PART}
        # 2026-11-03: tercera ronda de clones: 579.
        # 2026-11-04: clones de Lista 2 a respaldo de Lista 1: 549.
        # 2026-11-07: revisión de Lista 2 (clones por audio y guías comprobadas con fotograma): 499.
        self.assertGreaterEqual(len(claro), 480)
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
