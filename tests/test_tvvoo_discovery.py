import unittest

import discover_tvvoo_catalog as discovery


class TvVooDiscoveryTests(unittest.TestCase):
    def test_alias_normalization_does_not_double_encode(self) -> None:
        expected = "vavoo_SKY%20SPORTS%20F1%7Cgroup%3Auk"
        self.assertEqual(
            discovery.normalize_vavoo_id("vavoo_SKY SPORTS F1|group:uk"),
            expected,
        )
        self.assertEqual(
            discovery.normalize_vavoo_id(expected),
            expected,
        )

    def test_identity_collapses_quality_and_sports_plural(self) -> None:
        self.assertEqual(
            discovery.identity_key("Eleven Sports 1 HD"),
            discovery.identity_key("Eleven Sport 1 FHD"),
        )

    def test_adult_signals_are_classified_not_excluded(self) -> None:
        self.assertFalse(discovery.excluded_source_name("Private XXX HD"))
        self.assertEqual(
            discovery.category_for("Private XXX HD", ["Entertainment"]),
            "Adultos",
        )
        self.assertEqual(
            discovery.category_for("Penthouse", ["Movies"]),
            "Adultos",
        )

    def test_adult_signal_without_safe_logo_is_kept(self) -> None:
        groups = discovery.candidate_groups(
            [
                {
                    "type": "tv",
                    "id": "vavoo_Private%20Channel%7Cgroup%3Auk",
                    "name": "Private Channel",
                    "genres": ["Adult"],
                    "logo": "https://untrusted.example/private.png",
                }
            ],
            "uk",
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].category, "Adultos")
        self.assertEqual(groups[0].logo, "")

    def test_broad_sports_music_and_movie_classification(self) -> None:
        self.assertEqual(
            discovery.category_for("World Rugby", ["Sport"]),
            "Deportes",
        )
        self.assertEqual(
            discovery.category_for("Live Concerts", ["Music"]),
            "Música",
        )
        self.assertEqual(
            discovery.category_for("Cinema Classics", ["Movies"]),
            "Películas",
        )
        self.assertTrue(
            discovery.has_subtitle_hint(
                "Cinema VOST", ["Movies"], {"language": "Original Version"}
            )
        )

    def test_candidate_group_keeps_movie_subtitle_hint(self) -> None:
        groups = discovery.candidate_groups(
            [
                {
                    "type": "tv",
                    "id": "vavoo_Cinema%20VOST%7Cgroup%3Auk",
                    "name": "Cinema VOST HD",
                    "genres": ["Movies"],
                    "language": "Original Version",
                    "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/cinema.png",
                }
            ],
            "uk",
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].category, "Películas")
        self.assertTrue(groups[0].subtitle_hint)

    def test_logo_policy_rejects_placeholder_and_query_urls(self) -> None:
        self.assertEqual(
            discovery.safe_logo(
                "https://placehold.co/900x270/12052b/00FFD1.png?text=SKY"
            ),
            "",
        )
        self.assertEqual(
            discovery.safe_logo(
                "https://raw.githubusercontent.com/tv-logo/tv-logos/main/logo.png"
            ),
            "https://raw.githubusercontent.com/tv-logo/tv-logos/main/logo.png",
        )
        self.assertEqual(
            discovery.safe_logo(
                "https://raw.githubusercontent.com/tv-logo/tv-logos/main/logo.png?token=secret"
            ),
            "",
        )

    def test_selection_is_bounded_and_skips_existing_alias(self) -> None:
        groups = [
            discovery.CandidateGroup(
                region="uk",
                source_name="SKY SPORTS F1 HD",
                aliases=("vavoo_SKY%20SPORTS%20F1%20HD%7Cgroup%3Auk",),
                logo="https://raw.githubusercontent.com/tv-logo/tv-logos/main/f1.png",
                category="Deportes",
                base_key="SKY SPORT F1",
            ),
            discovery.CandidateGroup(
                region="it",
                source_name="Rai Sport",
                aliases=("vavoo_RAI%20SPORT%7Cgroup%3Ait",),
                logo="https://raw.githubusercontent.com/tv-logo/tv-logos/main/rai.png",
                category="Deportes",
                base_key="RAI SPORT",
            ),
            discovery.CandidateGroup(
                region="fr",
                source_name="C Star",
                aliases=("vavoo_C%20STAR%7Cgroup%3Afr",),
                logo="https://raw.githubusercontent.com/tv-logo/tv-logos/main/cstar.png",
                category="Música",
                base_key="C STAR",
            ),
        ]
        selected, stats = discovery.select_candidates(
            groups,
            existing_ids=set(),
            existing_aliases={"vavoo_SKY%20SPORTS%20F1%20HD%7Cgroup%3Auk"},
            existing_names=set(),
            existing_sidecar_count=0,
            max_new=1,
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][1].source_name, "Rai Sport")
        self.assertEqual(stats["duplicate_alias"], 1)

    def test_m3u_record_contains_stable_metadata_only(self) -> None:
        group = discovery.CandidateGroup(
            region="de",
            source_name="Sky Nature HD",
            aliases=("vavoo_SKY%20NATURE%20HD%7Cgroup%3Ade",),
            logo="https://raw.githubusercontent.com/tv-logo/tv-logos/main/nature.png",
            category="Misceláneos",
            base_key="SKY NATURE",
        )
        info_line, url_line = discovery.m3u_record(
            "Vavoo.de.SKYNATURE@TvVoo", group
        )
        self.assertIn('x-resolver="tvvoo"', info_line)
        self.assertIn("x-resolver-ids=\"vavoo_SKY%20NATURE%20HD%7Cgroup%3Ade\"", info_line)
        self.assertTrue(url_line.endswith(".json"))
        self.assertNotIn("token", info_line.lower() + url_line.lower())

    def test_missing_sidecar_entry_can_be_reconciled_without_network(self) -> None:
        channel_id = "Vavoo.uk.TESTCHANNEL@TvVoo"
        entry = {
            "name": "Test Channel Reino Unido",
            "aliases": ["vavoo_TEST%20CHANNEL%7Cgroup%3Auk"],
            "region": "uk",
            "sourceName": "TEST CHANNEL",
            "category": "Misceláneos",
            "logo": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/test.png",
        }
        records = discovery.missing_sidecar_records(
            ["#EXTM3U"], {channel_id: entry}
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0][0], channel_id)
        self.assertEqual(records[0][1].region, "uk")

    def test_discovery_sidecar_and_catalog_patch_version_are_valid(self) -> None:
        self.assertEqual(
            discovery.updater.next_catalog_version("2026.09.01.5"),
            "2026.09.01.6",
        )
        entries = discovery.updater.load_tvvoo_discovery_entries()
        self.assertGreaterEqual(len(entries), 24)
        self.assertTrue(
            all(
                discovery.updater.resolver_attributes_for(channel).get("x-resolver")
                == "tvvoo"
                for channel in discovery.updater.parse_channels(
                    discovery.CATALOG_PATH.read_text(encoding="utf-8-sig").splitlines()
                )
                if channel.tvg_id in entries
            )
        )


if __name__ == "__main__":
    unittest.main()
