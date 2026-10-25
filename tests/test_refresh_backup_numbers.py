"""scripts/refresh_backup_numbers.py (2026-10-24): números de backups.json al día por tvg-id."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from refresh_backup_numbers import refresh  # noqa: E402


class RefreshBackupNumbersTest(unittest.TestCase):
    def test_updates_numbers_by_tvg_id_and_reorders(self):
        backups = {"updated": "2026-01-01", "channels": {
            "A": {"display_name": "Canal A", "number": 10, "backups": [{"tvg_id": "x", "from_number": 99}]},
            "B": {"display_name": "Canal B", "number": 20, "backups": []},
        }}
        layout = {"channels": [{"tvgId": "A", "number": 30}, {"tvgId": "B", "number": 20}]}

        changes = refresh(backups, layout)

        self.assertEqual(["Canal A: 10 → 30"], changes)
        self.assertEqual(["B", "A"], list(backups["channels"]))
        self.assertEqual(99, backups["channels"]["A"]["backups"][0]["from_number"])
        self.assertNotEqual("2026-01-01", backups["updated"])

    def test_no_changes_leaves_the_file_as_is(self):
        backups = {"updated": "2026-01-01", "channels": {"A": {"number": 5, "backups": []}}}
        self.assertEqual([], refresh(backups, {"channels": [{"tvgId": "A", "number": 5}]}))
        self.assertEqual("2026-01-01", backups["updated"])

    def test_missing_row_is_not_invented(self):
        backups = {"channels": {"A": {"number": 5, "backups": []}}}
        self.assertEqual([], refresh(backups, {"channels": []}))
        self.assertEqual(5, backups["channels"]["A"]["number"])


if __name__ == "__main__":
    unittest.main()
