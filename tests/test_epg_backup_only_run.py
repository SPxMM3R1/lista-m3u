"""Corrida que solo descarga el respaldo de un canal (2026-11-14, TNT).

Una corrida de epgshare rehízo la guía de TNT (principal Claro, respaldo TNT México)
con la de México: la app mostró «Sing» cuando ya daban «Kung Fu Panda». Si la parte de
la fuente principal no se descargó, la guía anterior se conserva mientras cubra el futuro.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epg_fragments  # noqa: E402
import update_m3u  # noqa: E402
from tests.test_epg_fragments import NOW, guide  # noqa: E402

CHANNEL = "Canal.Prueba"


class BackupOnlyRunTests(unittest.TestCase):
    def run_build(self, old_fragment: bytes, fetched: set[str]) -> dict:
        new_guide = guide({CHANNEL: [(0, 2, "Del respaldo"), (2, 30, "Del respaldo 2")]}, "mx1")

        def fake_refresh(*_args, output_path, **_kwargs):
            Path(output_path).write_bytes(new_guide)
            return {}

        with tempfile.TemporaryDirectory() as tmp:
            fragments_dir = Path(tmp) / "canales"
            fragments_dir.mkdir()
            epg_fragments.write_fragment(fragments_dir, CHANNEL, old_fragment)
            with patch.object(update_m3u, "EPG_FRAGMENTS_DIR", fragments_dir), \
                 patch.object(update_m3u, "EPG_ROOT_META_PATH", Path(tmp) / "meta.json"), \
                 patch.object(update_m3u, "assemble_epg_from_fragments"), \
                 patch.object(update_m3u, "epg_scope_channels", return_value=([], {})), \
                 patch.object(update_m3u, "refresh_epg", side_effect=fake_refresh), \
                 patch.object(update_m3u, "epg_channel_parts",
                              return_value={update_m3u.CLARO_GUIDE_PART, update_m3u.EPGSHARE_PART}), \
                 patch.object(update_m3u, "epg_primary_part", return_value=update_m3u.CLARO_GUIDE_PART):
                return update_m3u.build_epg_fragments(None, fetched_parts=fetched, now=NOW)

    def test_backup_only_run_keeps_primary_guide(self):
        old = guide({CHANNEL: [(-1, 1, "De Claro"), (1, 30, "De Claro 2")]}, "claro-guia")
        result = self.run_build(old, {update_m3u.EPGSHARE_PART})
        self.assertEqual(result["changed"], [])
        self.assertIn(CHANNEL, result["kept"])

    def test_primary_run_replaces_guide(self):
        old = guide({CHANNEL: [(-1, 1, "De Claro"), (1, 30, "De Claro 2")]}, "claro-guia")
        result = self.run_build(old, {update_m3u.CLARO_GUIDE_PART})
        self.assertEqual(result["changed"], [CHANNEL])

    def test_backup_fills_when_old_guide_runs_out(self):
        old = guide({CHANNEL: [(-1, 1, "De Claro"), (1, 3, "De Claro 2")]}, "claro-guia")
        result = self.run_build(old, {update_m3u.EPGSHARE_PART})
        self.assertEqual(result["changed"], [CHANNEL])


if __name__ == "__main__":
    unittest.main()
