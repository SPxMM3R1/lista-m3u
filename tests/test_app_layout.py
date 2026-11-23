import json
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_app_layout  # noqa: E402


class AppLayoutTest(unittest.TestCase):
    def test_drops_deleted_rows_unless_still_published(self):
        layout = {
            "schemaVersion": 1,
            "excludedM3u": ["X.cl"],
            "approval": {"by": "editor"},
            "channels": [
                {"kind": "m3u", "tvgId": "A", "state": "active", "order": 1, "number": 1},
                {"kind": "m3u", "tvgId": "B", "state": "hidden", "order": 2, "number": 2},
                {"kind": "m3u", "tvgId": "C", "state": "deleted", "order": 3, "number": 3},
                {"kind": "m3u", "tvgId": "D", "state": "deleted", "order": 4, "number": 4},
                {"kind": "provider", "catalogKey": "uk|E", "state": "deleted", "order": 5, "number": 5},
            ],
        }
        result = build_app_layout.build(layout, {"D", "uk|E"})
        self.assertEqual(["A", "B", "D", "uk|E"],
                         [build_app_layout.row_identity(row) for row in result["channels"]])
        self.assertEqual(["X.cl"], result["excludedM3u"])
        self.assertEqual(1, result["schemaVersion"])
        self.assertNotIn("approval", result)

    def test_reads_tvg_and_resolver_identities(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "l.m3u"
            path.write_text('#EXTM3U\n#EXTINF:-1 tvg-id="A.cl" x-resolver-stable-id="uk|B",A\nhttp://x\n',
                            encoding="utf-8")
            self.assertEqual({"A.cl", "uk|B"}, build_app_layout.playlist_identities([path]))

    def test_published_file_matches_layout_rows(self):
        root = Path(__file__).resolve().parents[1]
        published = root / "data" / "app-layout.json"
        if not published.exists():
            self.skipTest("sin app-layout.json")
        app = json.loads(published.read_text(encoding="utf-8"))
        self.assertEqual(1, app["schemaVersion"])
        orders = [row["order"] for row in app["channels"]]
        self.assertEqual(len(orders), len(set(orders)))


if __name__ == "__main__":
    unittest.main()
