from __future__ import annotations

import json
import unittest

from scripts import build_site_data


class BuildSiteDataTests(unittest.TestCase):
    def test_playlist_export_contains_editorial_metadata_only(self) -> None:
        source = "\n".join(
            (
                "#EXTM3U",
                '#EXTINF:-1 tvg-id="news.one" tvg-name="News One" group-title="News",News One',
                "https://private.invalid/signed/playback.m3u8?token=do-not-export",
            )
        )

        rows = build_site_data.parse_playlist(source, "1.m3u")
        encoded = json.dumps(rows)

        self.assertEqual(rows[0]["tvgId"], "news.one")
        self.assertEqual(rows[0]["sourceList"], "1.m3u")
        self.assertNotIn("private.invalid", encoded)
        self.assertNotIn("token=", encoded)

    def test_provider_identity_registry_exports_only_canonical_names_and_ids(self) -> None:
        source = "\n".join(
            (
                "#EXTM3U",
                '#EXTINF:-1 tvg-id="SkySportsF1.uk" tvg-name="Sky Sports F1" x-resolver="highfly" x-resolver-id="f1-live" x-resolver-manifest="https://secret.invalid/manifest",Sky Sports F1',
                "https://secret.invalid/leaf/f1.m3u8?token=do-not-export",
                '#EXTINF:-1 tvg-id="Channel.one" tvg-name="Channel One",Channel One',
                "https://private.invalid/channel.m3u8",
                '#EXTINF:-1 tvg-id="token=do-not-export" tvg-name="Leaked",Leaked',
                '#EXTINF:-1 tvg-id="TvVoo.id@TvVoo" tvg-name="TvVoo Channel" x-resolver="tvvoo" x-resolver-id="vavoo_SECRET",TvVoo Channel',
                "https://private.invalid/tvvoo.m3u8",
            )
        )

        identities = build_site_data.parse_provider_identities(source)
        encoded = json.dumps(identities)

        self.assertEqual(
            identities,
            [
                {"catalogKey": "SkySportsF1.uk", "name": "Sky Sports F1"},
                {"catalogKey": "Channel.one", "name": "Channel One"},
            ],
        )
        self.assertNotIn("secret.invalid", encoded)
        self.assertNotIn("vavoo_SECRET", encoded)
        self.assertNotIn("token=", encoded)

    def test_initial_layout_numbers_one_combined_order(self) -> None:
        layout = build_site_data.initial_layout(
            [
                {"kind": "m3u", "tvgId": "one", "name": "One", "sourceList": "1.m3u"},
                {
                    "kind": "provider",
                    "provider": "highfly",
                    "catalogKey": "SportsF1.uk",
                    "providerResourceId": "leaf:f1-live",
                    "resolverSlug": "f1-live",
                    "name": "Sports F1",
                },
            ]
        )

        build_site_data.validate_layout(layout)
        self.assertEqual([row["number"] for row in layout["channels"]], [1, 2])
        self.assertEqual([row["order"] for row in layout["channels"]], [1, 2])

    def test_provider_alternates_share_one_stable_editor_row(self) -> None:
        rows = [
            {
                "provider": "highfly",
                "catalogKey": "SportsF1.uk",
                "providerResourceId": "leaf:f1-hd",
                "resolverSlug": "f1-hd",
                "order": 1,
                "name": "F1 HD",
            },
            {
                "provider": "highfly",
                "catalogKey": "SportsF1.uk",
                "providerResourceId": "leaf:f1-4k",
                "resolverSlug": "f1-4k",
                "order": 2,
                "name": "F1 4K",
            },
        ]

        unique = build_site_data._unique_provider_rows(rows)

        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["providerResourceId"], "leaf:f1-hd")
        self.assertEqual(unique[0]["name"], "F1 HD")

    def test_layout_rejects_highfly_locator_as_identity_reference_mismatch(self) -> None:
        layout = {
            "schemaVersion": 1,
            "channels": [
                {
                    "kind": "provider",
                    "provider": "highfly",
                    "catalogKey": "leaf:f1-live",
                    "providerResourceId": "leaf:f1-live",
                    "resolverSlug": "f1-live",
                    "order": 1,
                    "number": 1,
                    "state": "active",
                }
            ],
        }

        with self.assertRaises(ValueError):
            build_site_data.validate_layout(layout)

    def test_layout_keeps_permanent_m3u_tombstones_out_of_active_rows(self) -> None:
        layout = build_site_data.initial_layout([
            {"kind": "m3u", "tvgId": "one", "name": "One", "sourceList": "2.m3u"},
        ])
        layout["excludedM3u"] = ["purged-id"]
        build_site_data.validate_layout(layout)
        layout["excludedM3u"] = ["one"]
        with self.assertRaisesRegex(ValueError, "activo pero excluido"):
            build_site_data.validate_layout(layout)


if __name__ == "__main__":
    unittest.main()
