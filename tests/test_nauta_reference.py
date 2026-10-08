import json
from pathlib import Path
import hashlib
import unittest
from unittest import mock
import nauta_reference
import update_m3u as runner

ROOT = Path(__file__).resolve().parents[1]


class NautaReferenceTest(unittest.TestCase):
    def test_roundtrip_exact_name_with_region_and_slashes(self):
        for name in ["ESPN 1 | Chile", "South Park 24/7", "TUDN ", "El canal, HD"]:
            self.assertEqual(("cat_4", name), nauta_reference.parse_reference(nauta_reference.reference("cat_4", name)))

    def test_invalid_or_sensitive_locators_fail_closed(self):
        for url in ["vibem3u://resolver/nauta/cat_4%7CX?token=x", "vibem3u://user@resolver/nauta/cat_4%7CX",
                    "vibem3u://resolver/nauta/opaque-provider-id", "vibem3u://resolver/nauta/cat_4%7Chttps%3A%2F%2Fhost"]:
            self.assertIsNone(nauta_reference.parse_reference(url))

    def test_complete_snapshot_matches_list_layout_and_trial_epg_exclusion(self):
        fixture = json.loads((ROOT/"contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
        ids = {r["tvgId"] for r in fixture["channels"]}
        self.assertEqual(fixture["distinctNames"], len(ids))
        self.assertGreaterEqual(fixture["providerEntries"], len(ids))
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        new = [r for r in layout["channels"] if r.get("tvgId") in ids]
        self.assertEqual(len(ids), len(new))
        self.assertTrue(all(r["trial"] and r["state"] == "active" and r["sourceList"] == "1.m3u" for r in new))
        self.assertTrue(ids.issubset(runner.trial_m3u_ids()))
        self.assertTrue(ids.isdisjoint(c.tvg_id for c in runner.main_playlist_channels()))
        first = min(r["number"] for r in new)
        self.assertGreater(first, max(r["number"] for r in layout["channels"] if r["state"] == "active" and r.get("tvgId") not in ids))
        for file in ["m3u.m3u", "1.m3u", "channel-catalog.m3u"]:
            lines = (ROOT/file).read_text(encoding="utf-8").splitlines()
            channels = [c for c in runner.parse_channels(lines) if c.tvg_id in ids]
            self.assertEqual(ids, {c.tvg_id for c in channels})
            for c in channels:
                ref = nauta_reference.parse_reference(c.url)
                self.assertIsNotNone(ref)
                self.assertEqual(c.tvg_id, nauta_reference.channel_id(ref[1]))
                with mock.patch.object(runner, "fetch_channel_bytes", side_effect=AssertionError("No network")):
                    self.assertTrue(runner.check_channel(c).ok)
        self.assertEqual((ROOT/"m3u.m3u").read_bytes(), (ROOT/"1.m3u").read_bytes())

    def test_no_old_editorial_row_or_selection_was_changed(self):
        # Snapshot digest also works in Actions' shallow checkout, without Git history.
        current = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        current["channels"] = current["channels"][:253]
        digest = hashlib.sha256(json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual("ef4897616000212013a446e89f51f6c688945724c004b309767f2bbb88b5494b", digest)
        text = (ROOT/"data/vibem3u-selection.json").read_text(encoding="utf-8")
        self.assertEqual("66117ce417497d4ca3c3098ada8b74b93dba7353a3a794c062e690761dc96736", hashlib.sha256(text.encode()).hexdigest())
