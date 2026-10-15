"""Salud de canales (2026-10-15): no se reescribe si solo cambian horas de revisión."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import update_m3u  # noqa: E402

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def state(updated: str, checked: str, status: str = "functional", failures: int = 0) -> dict:
    return {
        "schema": 1,
        "updated_at": updated,
        "channels": {"0104": {
            "name": "TVN", "status": status, "consecutive_failures": failures,
            "last_checked_at": checked, "last_ok_at": checked,
            "last_resolver_validated_at": checked, "resolver_url_hash": "h",
        }},
    }


class HealthStateWriteTest(unittest.TestCase):
    def test_timestamp_only_change_within_a_day_is_not_written(self):
        previous = state("2026-10-15T06:00:00Z", "2026-10-15T06:00:00Z")
        current = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")
        self.assertFalse(update_m3u.health_state_needs_write(previous, current, NOW))

    def test_timestamps_are_refreshed_once_a_day(self):
        previous = state("2026-10-14T11:00:00Z", "2026-10-14T11:00:00Z")
        current = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")
        self.assertTrue(update_m3u.health_state_needs_write(previous, current, NOW))

    def test_any_real_change_is_written(self):
        previous = state("2026-10-15T06:00:00Z", "2026-10-15T06:00:00Z")
        failed = state("2026-10-15T12:00:00Z", "2026-10-15T06:00:00Z", "temporarily_unavailable", 1)
        self.assertTrue(update_m3u.health_state_needs_write(previous, failed, NOW))
        rotated = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")
        rotated["channels"]["0104"]["resolver_url_hash"] = "otro"
        self.assertTrue(update_m3u.health_state_needs_write(previous, rotated, NOW))
        added = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")
        added["channels"]["0105"] = {"name": "Mega"}
        self.assertTrue(update_m3u.health_state_needs_write(previous, added, NOW))

    def test_missing_or_bad_previous_state_is_written(self):
        current = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")
        self.assertTrue(update_m3u.health_state_needs_write({}, current, NOW))
        self.assertTrue(update_m3u.health_state_needs_write(state("x", "x"), state("y", "y"), NOW))

    def test_unchanged_channels_keep_recent_timestamps(self):
        previous = state("2026-10-15T06:00:00Z", "2026-10-15T06:00:00Z")["channels"]
        previous["0105"] = dict(previous["0104"], name="Mega")
        current = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")["channels"]
        current["0105"] = dict(current["0104"], name="Mega", status="temporarily_unavailable",
                               consecutive_failures=1)
        merged = update_m3u.keep_unchanged_health_timestamps(previous, current, NOW)
        self.assertEqual("2026-10-15T06:00:00Z", merged["0104"]["last_checked_at"])
        self.assertEqual("2026-10-15T12:00:00Z", merged["0105"]["last_checked_at"])
        self.assertEqual("temporarily_unavailable", merged["0105"]["status"])

    def test_old_timestamps_are_renewed(self):
        previous = state("2026-10-14T06:00:00Z", "2026-10-14T06:00:00Z")["channels"]
        current = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")["channels"]
        merged = update_m3u.keep_unchanged_health_timestamps(previous, current, NOW)
        self.assertEqual("2026-10-15T12:00:00Z", merged["0104"]["last_ok_at"])

    def test_new_channels_are_kept_as_is(self):
        current = state("2026-10-15T12:00:00Z", "2026-10-15T12:00:00Z")["channels"]
        self.assertEqual(current, update_m3u.keep_unchanged_health_timestamps({}, current, NOW))


if __name__ == "__main__":
    unittest.main()
