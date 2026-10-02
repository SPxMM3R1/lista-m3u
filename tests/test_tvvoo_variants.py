import unittest

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


if __name__ == "__main__":
    unittest.main()
