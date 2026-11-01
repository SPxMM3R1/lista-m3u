"""Los candidatos importados no pueden romper el arranque del runner por bajas previas."""
import unittest
from pathlib import Path

import update_m3u


class IptvOrgExclusionsTest(unittest.TestCase):
    def test_imported_rows_respect_permanent_exclusions(self):
        path = Path(__file__).resolve().parents[1] / "channel-catalog.m3u"
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        before = {c.tvg_id for c in update_m3u.parse_channels(lines)
                  if c.tvg_id.startswith("IPTVOrg.")}
        update_m3u.remove_permanently_removed_channels(lines, protected_ids=set())
        after = {c.tvg_id for c in update_m3u.parse_channels(lines)
                 if c.tvg_id.startswith("IPTVOrg.")}
        self.assertEqual(before, after, "La importación incluye canales excluidos permanentemente")


if __name__ == "__main__":
    unittest.main()
