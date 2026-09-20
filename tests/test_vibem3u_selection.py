import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import update_m3u
import vibem3u_selection


class VibeM3USelectionTest(unittest.TestCase):
    def write_manifest(self, payload: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "vibem3u-selection.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def base_manifest(self, channels: list[dict]) -> dict:
        return {
            "schemaVersion": 1,
            "source": "vibem3u-android",
            "selectionSignature": "a" * 64,
            "sources": [
                {"provider": "highfly", "enabled": True, "channels": channels}
            ],
        }

    def test_highfly_catalog_key_survives_resource_rotation(self) -> None:
        path = self.write_manifest(
            self.base_manifest(
                [
                    {
                        "provider": "highfly",
                        "catalogKey": "SkySportsTennis.uk",
                        "providerResourceId": "leaf:tennis-847291",
                        "resolverSlug": "tennis-847291",
                        "name": "Sky Sports Tennis",
                        "group": "Deportes",
                        "category": "Tennis",
                        "countryKey": "uk",
                        "identityState": "canonical",
                        "order": 1,
                    }
                ]
            )
        )
        document = vibem3u_selection.load_selection(path)
        channel = SimpleNamespace(
            tvg_id="SkySportsTennis.uk",
            name="Sky Sports Tennis",
            display_name="Sky Sports Tennis",
            info_line=1,
        )
        result = vibem3u_selection.reconcile_selection(
            document,
            [channel],
            [
                "#EXTM3U",
                '#EXTINF:-1 tvg-id="SkySportsTennis.uk",Sky Sports Tennis',
                "https://papacito.cfd/m3u/old/live.m3u8",
            ],
        )
        self.assertEqual(frozenset({"SkySportsTennis.uk"}), result.selected_catalog_ids)
        self.assertEqual("catalogKey=tvg-id", result.matched[0].match)

    def test_tvvoo_matches_by_encoded_resolver_alias(self) -> None:
        stable_id = "unitedkingdom|vavoo_SKY%201%7Cgroup%3Auk"
        path = self.write_manifest(
            {
                "schemaVersion": 1,
                "sources": [
                    {
                        "provider": "tvvoo",
                        "enabled": True,
                        "channels": [
                            {
                                "provider": "tvvoo",
                                "catalogKey": stable_id,
                                "providerResourceId": stable_id,
                                "name": "Sky 1",
                                "group": "Deportes",
                                "category": "Deportes",
                                "countryKey": "unitedkingdom",
                                "aliases": ["vavoo_SKY%201%7Cgroup%3Auk"],
                                "identityState": "canonical",
                                "order": 1,
                            }
                        ],
                    }
                ],
            }
        )
        document = vibem3u_selection.load_selection(path)
        channel = SimpleNamespace(
            tvg_id="Sky1.uk@TvVoo",
            name="Sky 1",
            display_name="Sky 1",
            info_line=1,
        )
        result = vibem3u_selection.reconcile_selection(
            document,
            [channel],
            [
                "#EXTM3U",
                '#EXTINF:-1 tvg-id="Sky1.uk@TvVoo" '
                'x-resolver-ids="vavoo_SKY%201%7Cgroup%3Auk",Sky 1',
                "https://example.invalid/live.m3u8",
            ],
        )
        self.assertEqual({"Sky1.uk@TvVoo"}, set(result.selected_catalog_ids))
        self.assertEqual("catalogKey=resolver-alias", result.matched[0].match)

    def test_provisional_and_missing_rows_stay_pending(self) -> None:
        path = self.write_manifest(
            self.base_manifest(
                [
                    {
                        "provider": "highfly",
                        "catalogKey": "Highfly.New.uk",
                        "providerResourceId": "leaf:new-123456",
                        "resolverSlug": "new-123456",
                        "name": "New",
                        "group": "Deportes",
                        "category": "Tennis",
                        "identityState": "provisional",
                        "order": 1,
                    },
                    {
                        "provider": "highfly",
                        "catalogKey": "SkySportsMissing.uk",
                        "providerResourceId": "leaf:missing-123456",
                        "resolverSlug": "missing-123456",
                        "name": "Missing",
                        "group": "Deportes",
                        "category": "Tennis",
                        "identityState": "canonical",
                        "order": 2,
                    },
                ]
            )
        )
        result = vibem3u_selection.reconcile_selection(
            vibem3u_selection.load_selection(path),
            [],
            ["#EXTM3U"],
        )
        self.assertEqual(0, len(result.matched))
        self.assertEqual(
            {"identity_provisional", "catalog_not_found"},
            {item["reason"] for item in result.pending},
        )

    def test_rejects_hls_and_mismatched_highfly_resource(self) -> None:
        payload = self.base_manifest(
            [
                {
                    "provider": "highfly",
                    "catalogKey": "SkySportsTennis.uk",
                    "providerResourceId": "leaf:tennis-847291",
                    "resolverSlug": "other-847291",
                    "name": "Sky Sports Tennis",
                    "group": "Deportes",
                    "category": "Tennis",
                    "identityState": "canonical",
                    "order": 1,
                    "playbackUrl": "https://example.invalid/live.m3u8",
                }
            ]
        )
        with self.assertRaises(vibem3u_selection.SelectionError):
            vibem3u_selection.load_selection(self.write_manifest(payload))

    def test_marker_round_trip(self) -> None:
        line = '#EXTINF:-1 tvg-id="SkySportsTennis.uk",Sky Sports Tennis'
        marked = vibem3u_selection.with_selection_marker(line, True)
        self.assertTrue(vibem3u_selection.selection_marker_is_managed(marked))
        self.assertFalse(
            vibem3u_selection.selection_marker_is_managed(
                vibem3u_selection.with_selection_marker(marked, False)
            )
        )

    def test_runner_marks_match_and_updates_only_highfly_reference(self) -> None:
        path = self.write_manifest(
            self.base_manifest(
                [
                    {
                        "provider": "highfly",
                        "catalogKey": "SkySportsTennis.uk",
                        "providerResourceId": "leaf:tennis-847291",
                        "resolverSlug": "tennis-847291",
                        "name": "Sky Sports Tennis",
                        "group": "Deportes",
                        "category": "Tennis",
                        "identityState": "canonical",
                        "order": 1,
                    }
                ]
            )
        )
        lines = [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="SkySportsTennis.uk" '
            'x-resolver="highfly" x-resolver-id="old-123456" '
            'x-resolver-manifest="https://sports.highfly.to/manifest.json" '
            'x-resolver-refresh="on_play",Sky Sports Tennis',
            "https://papacito.cfd/m3u/old-123456/live.m3u8",
        ]
        previous_runtime_map = dict(update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS)
        self.addCleanup(
            lambda: (
                update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS.clear(),
                update_m3u.HIGHFLY_RUNTIME_RESOLVER_CHANNELS.update(previous_runtime_map),
            )
        )
        document = vibem3u_selection.load_selection(path)
        reconciliation = vibem3u_selection.reconcile_selection(
            document, update_m3u.parse_channels(lines), lines
        )
        changed, updates = update_m3u.apply_vibem3u_selection(lines, reconciliation)
        self.assertTrue(changed)
        self.assertEqual(2, updates)
        self.assertIn('x-vibem3u-selection="managed"', lines[1])
        self.assertIn('x-resolver-id="tennis-847291"', lines[1])
        self.assertEqual(
            "https://papacito.cfd/m3u/tennis-847291/live.m3u8", lines[2]
        )


if __name__ == "__main__":
    unittest.main()
