"""scripts/measure_backup_quality.py (2026-10-31): medición de respaldos para el selector de la app."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("measure_backup_quality", ROOT / "scripts/measure_backup_quality.py")
measure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(measure)


class MeasureBackupQualityTest(unittest.TestCase):
    def test_summary_keeps_what_the_app_reads(self):
        self.assertEqual(
            {"height": 1080, "width": 1920, "fps": 29.97, "kbps": 2600, "ok": True},
            measure.summary({"ok": True, "height": 1080, "width": 1920, "fps": "30000/1001", "kbps": 2600}),
        )
        self.assertEqual(
            {"height": 0, "width": 0, "fps": 0.0, "kbps": 0, "ok": False},
            measure.summary({"ok": False, "fps": "0/0"}),
        )

    def test_summary_prefers_decoded_frame_rate(self):
        # 1080i: ffprobe declara 60000/1001 (campos) pero se decodifican 29,97 cuadros (OSD).
        self.assertEqual(29.97, measure.summary(
            {"ok": True, "height": 1080, "width": 1920, "fps": "60000/1001", "fps_measured": 29.97, "kbps": 3000}
        )["fps"])

    def test_principal_urls_skip_resolvers(self):
        with tempfile.TemporaryDirectory() as folder:
            playlist = Path(folder) / "m3u.m3u"
            playlist.write_text(
                '#EXTM3U\n#EXTINF:-1 tvg-id="a" x-resolver="tvn",TVN\nhttps://x/tvn.m3u8\n'
                '#EXTINF:-1 tvg-id="b",AXN\nhttp://x/axn.m3u8\n',
                encoding="utf-8",
            )
            self.assertEqual({"b": "http://x/axn.m3u8"}, measure.principal_urls(playlist))

    def test_apply_writes_principal_and_copies(self):
        doc = {"channels": {"b": {"display_name": "AXN", "backups": [{"tvg_id": "c", "url": "http://x/c"}]}}}
        results = {
            "b": {"height": 1080, "width": 1920, "fps": 30.0, "kbps": 1900, "ok": True},
            "c": {"height": 0, "width": 0, "fps": 0.0, "kbps": 0, "ok": False},
        }
        self.assertEqual(2, measure.apply(doc, results, "2026-10-31 12:00 UTC"))
        self.assertEqual(1900, doc["channels"]["b"]["principal_quality"]["kbps"])
        self.assertFalse(doc["channels"]["b"]["backups"][0]["quality"]["ok"])
        self.assertEqual("2026-10-31 12:00 UTC", doc["quality_measured"])


if __name__ == "__main__":
    unittest.main()
