import unittest
from unittest.mock import patch

import import_tvvoo_ar as importer
import update_m3u as updater


class TvVooArImportTests(unittest.TestCase):
    def test_missing_logos_and_quality_variants_are_kept_idempotently(self):
        entries = [
            {"name": "Example", "country": "Arabia", "logo": None},
            {"name": "Example HD", "country": "Arabia", "logo": None},
            {"name": "Other", "country": "Spain", "logo": None},
        ]
        doc, catalog, stats = importer.import_entries(entries, {"schemaVersion": 1, "channels": {}}, "#EXTM3U\n")
        self.assertEqual(stats["added"], 1)
        entry = next(iter(doc["channels"].values()))
        self.assertEqual(len(entry["aliases"]), 2)
        self.assertEqual(entry["logo"], "")
        self.assertNotIn('tvg-country="AR"', catalog)
        _, second, stats = importer.import_entries(entries, doc, catalog)
        self.assertEqual(stats["added"], 0)
        self.assertEqual(catalog, second)

    def test_unicode_channels_are_distinct_and_encoded(self):
        entries = [
            {"name": "TV العربية", "country": "Arabia"},
            {"name": "TV الجزيرة", "country": "Arabia"},
            {"name": "Channel [NOT 24/7]", "country": "Arabia"},
        ]
        doc, _, stats = importer.import_entries(entries, {"schemaVersion": 1, "channels": {}}, "#EXTM3U\n")
        self.assertEqual(stats["added"], 3)
        self.assertEqual(len(doc["channels"]), 3)
        updater.validate_tvvoo_discovery_document(doc)

    def test_existing_alias_is_not_added_under_another_id(self):
        catalog = '#EXTM3U\n#EXTINF:-1 tvg-id="existing" x-resolver-ids="vavoo_ESPN%203%7Cgroup%3Aar",ESPN 3\nhttps://example.invalid\n'
        _, after, stats = importer.import_entries(
            [{"name": "ESPN 3", "country": "Arabia"}],
            {"schemaVersion": 1, "channels": {}}, catalog,
        )
        self.assertEqual(stats["existing"], 1)
        self.assertEqual(after, catalog)

    def test_ar_group_is_excluded_from_public_list_but_kept_for_retry(self):
        ar = updater.Channel(name="TRT ar", tvg_id="Vavoo.ar.TRT@TvVoo", url="https://example.invalid", url_line=0)
        other = updater.Channel(name="TRT de", tvg_id="Vavoo.de.TRT@TvVoo", url="https://example.invalid", url_line=0)
        with patch.object(updater, "TVVOO_STREAM_RESOLVER_IDS", {
            ar.name: ("vavoo_TRT%7Cgroup%3Aar",),
            other.name: ("vavoo_TRT%7Cgroup%3Ade",),
        }):
            self.assertFalse(updater.is_permanently_removed_channel(ar))
            self.assertTrue(updater.is_permanently_removed_channel(other))
            self.assertFalse(updater.external_vavoo_channel_is_allowed(ar))
            self.assertFalse(updater.external_vavoo_channel_is_allowed(other))
            self.assertEqual(updater.external_publication_channel_ids([ar], {ar.tvg_id}, set()), frozenset())
            self.assertEqual(updater.external_available_ids_from_health([ar], {ar.tvg_id}, {}), frozenset())
            self.assertEqual(updater.external_available_ids_from_health([ar], {ar.tvg_id}, {"channels": {ar.tvg_id: {"status": "functional"}}}), {ar.tvg_id})


if __name__ == "__main__":
    unittest.main()
