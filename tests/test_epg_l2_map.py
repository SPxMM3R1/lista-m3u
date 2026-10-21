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
        self.assertGreaterEqual(len(mapping), 1150)
        lines = (ROOT / "m3u-externa.m3u").read_text(encoding="utf-8").splitlines()
        published = set(re.findall(r'tvg-id="([^"]+)"', "\n".join(lines)))
        self.assertTrue(set(mapping).issubset(published))
        for target_id, (source, source_id) in mapping.items():
            with self.subTest(channel=target_id):
                self.assertIn(source, update_m3u.EPG_SOURCES)
                self.assertTrue(source_id)

    def test_scope_includes_the_mapped_lista2_channels(self):
        scope, ids = update_m3u.epg_scope_channels()
        mapping = update_m3u.load_epg_l2_map()
        self.assertTrue(set(mapping).issubset(ids))
        self.assertGreaterEqual(len(scope), 1200)


if __name__ == "__main__":
    unittest.main()
