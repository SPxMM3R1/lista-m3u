import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import highfly_live
import update_m3u


def row(key="SkySportsF1.uk", name="SKY SPORTS F1", slug="now-545445", state="active"):
    return {"provider": "highfly", "catalogKey": key, "name": name,
            "resolverSlug": slug, "providerResourceId": f"leaf:{slug}", "state": state}


class HighflyLiveTest(unittest.TestCase):
    def test_sync_updates_stale_slug_and_keeps_a_valid_approval(self) -> None:
        from tests.catalog_approval import approved_by_user, layout_approval_digest
        layout = {"schemaVersion": 1, "excludedM3u": [], "channels": [
            row(key="SkySportsF1UHD.uk", name="SKY SPORTS F1 UHD", slug="now-34343434")]}
        layout["approval"] = {"source": "editor", "sha256": layout_approval_digest(layout)}
        changes = highfly_live.sync_layout_document(layout, {"SkySportsF1UHD.uk": "now-4344344"})
        self.assertEqual(["SkySportsF1UHD.uk: now-34343434 → now-4344344"], changes)
        self.assertEqual("now-4344344", layout["channels"][0]["resolverSlug"])
        self.assertEqual("leaf:now-4344344", layout["channels"][0]["providerResourceId"])
        self.assertTrue(approved_by_user(layout))
        self.assertEqual("editor", layout["approval"]["source"])

    def test_sync_never_stamps_an_unapproved_layout(self) -> None:
        layout = {"schemaVersion": 1, "excludedM3u": [], "channels": [row(slug="now-545445")]}
        highfly_live.sync_layout_document(layout, {"SkySportsF1.uk": "now-344343"})
        self.assertNotIn("approval", layout)

    def test_sync_ignores_invalid_or_equal_slugs_and_other_providers(self) -> None:
        rows = [row(slug="now-344343"), {"provider": "tvvoo", "catalogKey": "SkySportsF1.uk"}]
        self.assertEqual([], highfly_live.sync_slugs(rows, {"SkySportsF1.uk": "now-344343"}))
        self.assertEqual([], highfly_live.sync_slugs([row()], {"SkySportsF1.uk": "../evil"}))
        self.assertEqual("now-545445", row()["resolverSlug"])

    def test_sync_files_writes_layout_and_selection_in_the_same_format(self) -> None:
        layout = {"schemaVersion": 1, "excludedM3u": [], "channels": [row(slug="now-545445")]}
        selection = {"schemaVersion": 1, "sources": [{"provider": "highfly", "channels": [
            {"provider": "highfly", "catalogKey": "SkySportsF1.uk", "resolverSlug": "now-545445",
             "providerResourceId": "leaf:now-545445", "order": 1}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            lp, sp = Path(tmp) / "layout.json", Path(tmp) / "selection.json"
            lp.write_text(highfly_live._dump(layout), encoding="utf-8")
            sp.write_text(highfly_live._dump(selection), encoding="utf-8")
            applied = highfly_live.sync_files({"SkySportsF1.uk": "now-344343"}, lp, sp)
            self.assertEqual(2, len(applied))
            self.assertEqual("now-344343", json.loads(lp.read_text(encoding="utf-8"))["channels"][0]["resolverSlug"])
            saved = json.loads(sp.read_text(encoding="utf-8"))
            self.assertEqual("leaf:now-344343", saved["sources"][0]["channels"][0]["providerResourceId"])

    def test_sync_files_skips_a_file_with_an_unexpected_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lp = Path(tmp) / "layout.json"
            lp.write_text(json.dumps({"channels": [row()]}), encoding="utf-8")
            self.assertEqual([], highfly_live.sync_files({"SkySportsF1.uk": "now-344343"}, lp, Path(tmp) / "no.json"))
            self.assertIn("now-545445", lp.read_text(encoding="utf-8"))

    def test_publishes_the_editor_leaf_when_it_has_signal(self) -> None:
        document = highfly_live.build_document(
            [row()], fetch=lambda slug: ["https://papacito.cfd/m3u/x/live.m3u8"],
            now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))

        self.assertEqual([{"catalogKey": "SkySportsF1.uk", "slug": "now-545445",
                           "url": "https://papacito.cfd/m3u/now-545445/live.m3u8"}], document["channels"])
        self.assertEqual("2026-09-28T12:00:00Z", document["generatedAt"])

    def test_falls_back_to_another_leaf_of_the_same_channel(self) -> None:
        with patch.dict(update_m3u.HIGHFLY_RUNTIME_VARIANTS, {"skysportsf1": ["now-545445", "now-34343434"]}, clear=True):
            document = highfly_live.build_document(
                [row()], fetch=lambda slug: [] if slug == "now-545445" else ["ok"])
        self.assertEqual("now-34343434", document["channels"][0]["slug"])

    def test_uhd_channel_falls_back_to_the_free_fhd_leaf(self) -> None:
        # Decisión 2026-10-03: sin Premium, la fila UHD publica la FHD gratuita como respaldo.
        uhd = row(key="SkySportsF1UHD.uk", name="SKY SPORTS F1 UHD", slug="now-34343434")
        with patch.dict(update_m3u.HIGHFLY_RUNTIME_VARIANTS, {"skysportsf1": ["now-34343434", "now-545445"]}, clear=True):
            document = highfly_live.build_document(
                [uhd], fetch=lambda slug: [] if slug == "now-34343434" else ["ok"])
        self.assertEqual("now-545445", document["channels"][0]["slug"])

    def test_premium_locked_leaf_is_reported(self) -> None:
        reasons = []
        def fetch(slug):
            raise ValueError("hoja Highfly bloqueada por Premium")
        self.assertIsNone(highfly_live.live_slug(row(), fetch, reasons))
        self.assertIn("Premium", reasons[0])

    def test_channel_without_signal_is_not_published(self) -> None:
        document = highfly_live.build_document([row()], fetch=lambda slug: [])
        self.assertEqual([], document["channels"])

    def test_only_active_highfly_rows_are_used(self) -> None:
        layout = {"channels": [row(), row(key="X", state="trash"), {"provider": "tvvoo", "catalogKey": "Y"}]}
        self.assertEqual(["SkySportsF1.uk"], [r["catalogKey"] for r in highfly_live.active_highfly_rows(layout)])

    def test_published_link_carries_no_token(self) -> None:
        document = highfly_live.build_document([row()], fetch=lambda slug: ["ok"])
        url = document["channels"][0]["url"]
        self.assertTrue(update_m3u.is_highfly_leaf_url(url))
        self.assertNotIn("?", url)

    def test_timestamp_alone_does_not_rewrite_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "highfly-live.json"
            first = highfly_live.build_document([row()], fetch=lambda slug: ["ok"],
                                                now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))
            self.assertTrue(highfly_live.write_if_changed(first, path))
            later = highfly_live.build_document([row()], fetch=lambda slug: ["ok"],
                                                now=datetime(2026, 9, 28, 13, tzinfo=timezone.utc))
            self.assertFalse(highfly_live.write_if_changed(later, path))
            self.assertEqual("2026-09-28T12:00:00Z", json.loads(path.read_text(encoding="utf-8"))["generatedAt"])

    def test_unchanged_links_renew_the_timestamp_every_three_hours(self) -> None:
        # La app deja de usar el archivo con más de 24 h: la fecha no puede quedarse pegada.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "highfly-live.json"
            first = highfly_live.build_document([row()], fetch=lambda slug: ["ok"],
                                                now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))
            highfly_live.write_if_changed(first, path)
            later = highfly_live.build_document([row()], fetch=lambda slug: ["ok"],
                                                now=datetime(2026, 9, 28, 15, tzinfo=timezone.utc))
            self.assertTrue(highfly_live.write_if_changed(later, path))
            self.assertEqual("2026-09-28T15:00:00Z", json.loads(path.read_text(encoding="utf-8"))["generatedAt"])


if __name__ == "__main__":
    unittest.main()
