import unittest

import catalog_approval

# Mismo ejemplo y mismo digest que tests/app-requests.test.mjs: si JS y Python dejan de
# coincidir, el sello del editor nunca validaría y las fotos fijas volverían a estorbar.
FIXTURE = {
    "schemaVersion": 1,
    "excludedM3u": ["PublicDirect.x"],
    "channels": [{
        "kind": "m3u", "tvgId": "0104", "name": "TVN «HD» ñandú | 24/7", "group": "Nacionales",
        "sourceList": "1.m3u", "order": 1, "number": 1, "state": "deleted",
    }],
}
DIGEST = "002cce3d08ee144e979dbb8bed8f1fe3959af44aaf0d6c60eb05574d2020bf4a"


class CatalogApprovalTest(unittest.TestCase):
    def test_digest_matches_the_editor(self):
        self.assertEqual(DIGEST, catalog_approval.layout_approval_digest(FIXTURE))

    def test_only_an_intact_stamp_from_editor_or_app_counts(self):
        stamped = {**FIXTURE, "approval": {"source": "editor", "sha256": DIGEST}}
        self.assertTrue(catalog_approval.approved_by_user(stamped))
        self.assertTrue(catalog_approval.approved_by_user({**stamped, "approval": {"source": "app", "sha256": DIGEST}}))
        self.assertTrue(catalog_approval.approved_by_user({**stamped, "approval": {"source": "chat", "sha256": DIGEST}}))
        self.assertFalse(catalog_approval.approved_by_user({**stamped, "approval": {"source": "agente", "sha256": DIGEST}}))
        self.assertFalse(catalog_approval.approved_by_user(FIXTURE))
        edited = {**stamped, "channels": [{**FIXTURE["channels"][0], "number": 2}]}
        self.assertFalse(catalog_approval.approved_by_user(edited))


if __name__ == "__main__":
    unittest.main()
