"""Override EPG con «primary» (2026-11-22, TVN).

Pedido del usuario: «La programación del primer canal del TVN está mal, debería decir MasterChef,
y dice Moisés». Zapping (que mandaba sobre cualquier override) daba Moisés; GatoTV, MasterChef.
Con "primary": true el override va primero y la oficial y Zapping solo rellenan.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import update_m3u


class EpgOverridePrimaryTest(unittest.TestCase):
    def chain_with(self, entry):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "epg-overrides.json"
            path.write_text(json.dumps({"channels": {"0104": entry}}), encoding="utf-8")
            with patch.dict(update_m3u.EPG_PROGRAMME_SOURCES), \
                    patch.dict(update_m3u.GATOTV_CHANNELS), \
                    patch.dict(update_m3u.EPGSHARE_BACKUP_CHANNELS), \
                    patch.dict(update_m3u.EPG_SHIFT_BY_TARGET), \
                    patch.object(update_m3u, "EPG_OVERRIDE_PRIMARY_IDS", set()):
                update_m3u.apply_epg_overrides(path)
                return update_m3u.epg_source_chain("0104")

    def test_primary_override_goes_before_zapping(self):
        chain = self.chain_with({"source": "gatotv", "source_id": "gatotv:tvn_chile", "primary": True})
        self.assertEqual(("gatotv", "gatotv:tvn_chile"), chain[0])
        self.assertIn((update_m3u.ZAPPING_EPG_SOURCE, "0104"), chain[1:])

    def test_plain_override_keeps_zapping_first(self):
        chain = self.chain_with({"source": "gatotv", "source_id": "gatotv:tvn_chile"})
        self.assertLess(chain.index((update_m3u.ZAPPING_EPG_SOURCE, "0104")),
                        chain.index(("gatotv", "gatotv:tvn_chile")))

    def test_published_tvn_override_is_primary_gatotv(self):
        data = json.loads(Path(update_m3u.EPG_OVERRIDES_PATH).read_text(encoding="utf-8"))
        entry = data["channels"]["0104"]
        self.assertEqual(("gatotv", "gatotv:tvn_chile", True),
                         (entry["source"], entry["source_id"], entry.get("primary")))


if __name__ == "__main__":
    unittest.main()
