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
        audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
        removed = {r["tvgId"] for r in audit["channels"] if r["decision"] == "remove"}
        ids -= removed
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
        current["excludedM3u"] = [id for id in current["excludedM3u"] if not id.endswith("@Nauta")]
        digest = hashlib.sha256(json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual("ef4897616000212013a446e89f51f6c688945724c004b309767f2bbb88b5494b", digest)
        text = (ROOT/"data/vibem3u-selection.json").read_text(encoding="utf-8")
        self.assertEqual("66117ce417497d4ca3c3098ada8b74b93dba7353a3a794c062e690761dc96736", hashlib.sha256(text.encode()).hexdigest())

    def test_cleanup_has_repeated_evidence_and_cannot_resurrect_removed_rows(self):
        audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
        fixture = json.loads((ROOT/"contracts/nauta-trial-channels-20261007.json").read_text(encoding="utf-8"))
        self.assertEqual({r["tvgId"] for r in fixture["channels"]}, {r["tvgId"] for r in audit["channels"]})
        removed = {r["tvgId"] for r in audit["channels"] if r["decision"] == "remove"}
        retained = {r["tvgId"] for r in audit["channels"] if r["decision"] == "retain"}
        self.assertEqual((533, 394, 139), (audit["reviewed"], len(retained), len(removed)))
        for row in audit["channels"]:
            checks = row["checks"]
            if row["decision"] == "retain":
                self.assertTrue(any(c["status"] == "video_ok" and c["decoded"] and c["appResolved"] for c in checks))
            else:
                self.assertEqual(3, len(checks))
                self.assertTrue(all(c["status"] == row["reason"] for c in checks))
                self.assertNotIn("video_ok", [c["status"] for c in checks])
                if row["reason"] == "provider_update_slate":
                    self.assertTrue(all(c["decoded"] and c["frameSha256"] in audit["verifiedUpdateSlateSha256"] for c in checks))
                elif row["reason"] == "playback_connection_error":
                    self.assertTrue(all(c["mediaHttpCodes"] and set(c["mediaHttpCodes"]) == {404} for c in checks))
                else:
                    self.assertEqual("provider_name_missing", row["reason"])
        layout = json.loads((ROOT/"data/channel-editor-layout.json").read_text(encoding="utf-8"))
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        self.assertTrue(removed.issubset(layout["excludedM3u"]))
        self.assertTrue(removed.issubset(presentation["excluded_m3u"]))
        self.assertTrue(removed.isdisjoint(r.get("tvgId") for r in layout["channels"]))
        self.assertTrue(removed.isdisjoint(presentation["trial_m3u"]))
        for order in presentation["orders"].values():
            self.assertTrue(removed.isdisjoint(order))
        for file in ["1.m3u", "m3u.m3u", "channel-catalog.m3u", "2.m3u", "m3u-externa.m3u"]:
            self.assertTrue(removed.isdisjoint(c.tvg_id for c in runner.parse_channels((ROOT/file).read_text(encoding="utf-8").splitlines())))
        expected = {r["tvgId"]: (r["number"], r["order"]) for r in audit["preservedRows"]}
        self.assertEqual(expected, {r["tvgId"]: (r["number"], r["order"]) for r in layout["channels"] if r.get("tvgId") in retained})
        for name in ["ESPN 1 | Chile", "DSports 2 HD"]:
            control = next(r for r in audit["channels"] if r["name"] == name)
            self.assertEqual(["video_ok"] * 3, [c["status"] for c in control["checks"]])

    def test_cleanup_preserves_other_presentation_and_contains_no_secrets(self):
        audit = json.loads((ROOT/"contracts/nauta-validation-20261008.json").read_text(encoding="utf-8"))
        def strip_nauta(value):
            if isinstance(value, list):
                return [strip_nauta(v) for v in value if not (isinstance(v, str) and v.endswith("@Nauta"))]
            if isinstance(value, dict):
                return {k: strip_nauta(v) for k, v in value.items() if not k.endswith("@Nauta")}
            return value
        presentation = json.loads((ROOT/"presentation-overrides.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(json.dumps(strip_nauta(presentation), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(audit["nonNautaPresentationSha256"], digest)
        allowed = {"atUtc", "status", "appResolved", "decoded", "audioDetected", "mediaHttpCodes", "apiHttpCodes", "frameSha256"}
        self.assertTrue(all(set(c).issubset(allowed) for r in audit["channels"] for c in r["checks"]))
        self.assertTrue(all(not c["apiHttpCodes"] for r in audit["channels"] for c in r["checks"]))
