import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import tvvoo_variants as tv


def entries(code, *names):
    return [(tv.canonical_alias(f"vavoo_{name}|group:{code}", code), name) for name in names]


class TvVooVariantRules(unittest.TestCase):
    def test_quality_and_backup_marks_are_removed(self) -> None:
        for name in ("SKY SPORTS MIX HD", "SKY SPORTS MIX FHD", "SKY SPORTS MIX (BACKUP)",
                     "SKY SPORTS MIX HD (BACKUP 2)", "SKY SPORTS MIX UHD", "SKY SPORTS MIX HD+",
                     "SKY SPORTS MIX HEVC", "SKY SPORTS MIX (H265)"):
            self.assertEqual("SKY SPORTS MIX", tv.base_name(name), name)

    def test_sport_and_sports_are_different_channels(self) -> None:
        # En Alemania «SKY SPORT F1» es la señal alemana y «SKY SPORTS F1» la inglesa.
        self.assertNotEqual(tv.base_name("SKY SPORT F1 HD"), tv.base_name("SKY SPORTS F1 HD"))

    def test_numbers_are_kept(self) -> None:
        self.assertNotEqual(tv.base_name("TNT SPORTS 1"), tv.base_name("TNT SPORTS 10 HD"))

    def test_doubtful_entries_are_never_siblings(self) -> None:
        for name in ("SKY SPORT 2 (MATCH TIME)", "SKY SPORT 1 [LIVE DURING EVENTS ONLY]",
                     "SKY SPORT F1 HD (LOCAL)", "SKY SPORT F1 RAW"):
            self.assertIsNone(tv.base_name(name), name)

    def test_siblings_keep_the_choice_out_and_order_by_quality(self) -> None:
        catalog = entries("uk", "SKY SPORTS MIX", "SKY SPORTS MIX (BACKUP)", "SKY SPORTS MIX HD",
                          "SKY SPORTS MIX FHD", "SKY SPORT MIX", "SKY SPORTS MAIN EVENT")
        selected = catalog[0][0]
        names = dict(catalog)
        self.assertEqual(
            ["SKY SPORTS MIX FHD", "SKY SPORTS MIX HD", "SKY SPORTS MIX (BACKUP)"],
            [names[alias] for alias in tv.siblings_for(selected, catalog)],
        )

    def test_countries_never_mix(self) -> None:
        layout = {"channels": [{
            "kind": "provider", "provider": "tvvoo", "state": "active", "countryKey": "germany",
            "catalogKey": "germany|" + tv.canonical_alias("vavoo_SKY SPORTS F1|group:de", "de"),
        }]}
        catalogs = {
            "de": {"metas": [{"id": "vavoo_SKY SPORTS F1|group:de", "name": "SKY SPORTS F1"},
                             {"id": "vavoo_SKY SPORT F1 HD|group:de", "name": "SKY SPORT F1 HD"}]},
            "uk": {"metas": [{"id": "vavoo_SKY SPORTS F1 HD|group:uk", "name": "SKY SPORTS F1 HD"}]},
        }
        channels, errors = tv.build_variants(layout, fetch=lambda code: catalogs[code])
        self.assertEqual({}, errors)
        self.assertEqual({}, channels)

    def test_alias_encoding_matches_the_editor(self) -> None:
        self.assertEqual(
            "vavoo_SKY%20SPORTS%20MIX%20%28BACKUP%29%7Cgroup%3Auk",
            tv.canonical_alias("vavoo_SKY SPORTS MIX (BACKUP)|group:uk", "uk"),
        )


class TvVooVariantPersistence(unittest.TestCase):
    key = "unitedkingdom|vavoo_A%7Cgroup%3Auk"

    def test_a_sibling_missing_once_is_kept(self) -> None:
        previous = {"channels": {self.key: ["vavoo_A%20HD"]}}
        merged, missing = tv.merge_with_previous({}, previous, {self.key}, set())
        self.assertEqual({self.key: ["vavoo_A%20HD"]}, merged)
        self.assertEqual({f"{self.key} vavoo_A%20HD": 1}, missing)

    def test_a_sibling_missing_three_runs_is_dropped(self) -> None:
        previous = {"channels": {self.key: ["vavoo_A%20HD"]},
                    "missing": {f"{self.key} vavoo_A%20HD": tv.MISSING_RUNS_BEFORE_DROP - 1}}
        merged, missing = tv.merge_with_previous({}, previous, {self.key}, set())
        self.assertEqual({}, merged)
        self.assertEqual({}, missing)

    def test_unselected_channels_are_removed(self) -> None:
        previous = {"channels": {self.key: ["vavoo_A%20HD"]}}
        merged, _ = tv.merge_with_previous({}, previous, set(), set())
        self.assertEqual({}, merged)


class TvVooVariantFreshness(unittest.TestCase):
    now = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    key = "unitedkingdom|vavoo_A%7Cgroup%3Auk"
    alias = "vavoo_A%20HD%7Cgroup%3Auk"

    def previous(self, age: timedelta) -> dict:
        return {
            "schema": 1,
            "generatedAt": (self.now - age).isoformat().replace("+00:00", "Z"),
            "channels": {self.key: [self.alias]},
            "missing": {},
        }

    def run_main(self, previous: dict, errors: dict | None = None, channels: dict | None = None) -> dict:
        layout = {"channels": [{
            "kind": "provider", "provider": "tvvoo", "state": "active",
            "countryKey": "unitedkingdom", "catalogKey": self.key,
        }]}
        current = previous["channels"] if channels is None else channels
        with tempfile.TemporaryDirectory() as directory:
            layout_path = Path(directory) / "layout.json"
            output_path = Path(directory) / "variants.json"
            layout_path.write_text(json.dumps(layout), encoding="utf-8")
            output_path.write_text(json.dumps(previous), encoding="utf-8")
            with (patch.object(tv, "LAYOUT_PATH", layout_path),
                  patch.object(tv, "OUTPUT_PATH", output_path),
                  patch.object(tv, "build_variants", return_value=(current, errors or {})),
                  patch.object(tv, "datetime", wraps=datetime) as clock):
                clock.now.return_value = self.now
                self.assertEqual(0, tv.main())
            return json.loads(output_path.read_text(encoding="utf-8"))

    def test_unchanged_eight_day_old_variants_are_refreshed(self) -> None:
        previous = self.previous(timedelta(days=8))
        published = self.run_main(previous)
        self.assertEqual("2026-10-02T12:00:00Z", published["generatedAt"])
        self.assertEqual(previous["channels"], published["channels"])
        self.assertEqual(previous["missing"], published["missing"])

    def test_timestamp_is_refreshed_at_twenty_four_hours(self) -> None:
        published = self.run_main(self.previous(timedelta(hours=24)))
        self.assertEqual("2026-10-02T12:00:00Z", published["generatedAt"])

    def test_fresh_unchanged_variants_do_not_create_a_timestamp_only_update(self) -> None:
        previous = self.previous(timedelta(hours=23, minutes=59))
        self.assertEqual(previous, self.run_main(previous))

    def test_failed_catalog_does_not_refresh_retained_variants(self) -> None:
        previous = self.previous(timedelta(days=8))
        self.assertEqual(previous, self.run_main(previous, errors={"uk": "TimeoutError"}, channels={}))

    def test_partial_catalog_failure_does_not_refresh_unchanged_variants(self) -> None:
        previous = self.previous(timedelta(days=8))
        self.assertEqual(previous, self.run_main(previous, errors={"de": "TimeoutError"}))

    def test_missing_invalid_naive_or_future_timestamp_is_repaired(self) -> None:
        for timestamp in (None, "invalid", "2026-10-01T12:00:00", "2026-10-03T12:00:00Z"):
            with self.subTest(timestamp=timestamp):
                previous = self.previous(timedelta(days=8))
                previous["generatedAt"] = timestamp
                published = self.run_main(previous)
                self.assertEqual("2026-10-02T12:00:00Z", published["generatedAt"])

    def test_empty_variants_do_not_need_a_heartbeat(self) -> None:
        previous = self.previous(timedelta(days=8))
        previous["channels"] = {}
        self.assertEqual(previous, self.run_main(previous))

    def test_changed_variants_are_written_even_before_twenty_four_hours(self) -> None:
        previous = self.previous(timedelta(hours=1))
        new_alias = "vavoo_A%20FHD%7Cgroup%3Auk"
        published = self.run_main(previous, channels={self.key: [new_alias, self.alias]})
        self.assertEqual("2026-10-02T12:00:00Z", published["generatedAt"])
        self.assertEqual([new_alias, self.alias], published["channels"][self.key])


if __name__ == "__main__":
    unittest.main()
