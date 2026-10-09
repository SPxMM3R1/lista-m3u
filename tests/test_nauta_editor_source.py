import json
from pathlib import Path
import tempfile
import unittest

import nauta_reference
import update_m3u as runner


class NautaEditorSourceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout_path = Path(self.temp.name) / "channel-editor-layout.json"
        self.name = " ESPN 1 | Chile"
        self.channel_id = nauta_reference.channel_id(self.name)
        self.row = {
            "kind": "m3u",
            "tvgId": self.channel_id,
            "name": "ESPN 1 | Chile [Nauta]",
            "group": "Nauta · Deportes",
            "category": "Deportes",
            "sourceList": "1.m3u",
            "trial": True,
            "state": "active",
            "order": 607,
            "number": 620,
            "nautaCatalog": "cat_4",
            "nautaName": self.name,
        }

    def write_layout(self, row=None):
        self.layout_path.write_text(json.dumps({"schemaVersion": 1, "channels": [row or self.row]}), encoding="utf-8")

    def test_materializes_a_stable_tokenless_list1_trial_row_and_is_idempotent(self):
        self.write_layout()
        lines = ["#EXTM3U"]

        self.assertTrue(runner.apply_editor_nauta_channels(lines, self.layout_path))
        channels = runner.parse_channels(lines)
        self.assertEqual(1, len(channels))
        channel = channels[0]
        self.assertEqual(self.channel_id, channel.tvg_id)
        self.assertEqual(("cat_4", self.name), nauta_reference.parse_reference(channel.url))
        self.assertEqual({"x-resolver": "nauta", "x-resolver-refresh": "on_play"}, runner.resolver_attributes_for(channel))
        self.assertEqual(frozenset({self.channel_id}), runner.trial_m3u_ids({"trial_m3u": [self.channel_id]}))
        self.assertTrue(runner.apply_editor_nauta_channels(lines, self.layout_path) is False)
        self.assertEqual(3, len(lines))

    def test_rejects_a_public_id_that_does_not_hash_the_exact_source_name(self):
        row = dict(self.row, tvgId="Nauta.000000000000000000000000@Nauta")
        self.write_layout(row)

        with self.assertRaisesRegex(ValueError, "no coincide con el nombre exacto"):
            runner.apply_editor_nauta_channels(["#EXTM3U"], self.layout_path)

    def test_requires_list1_and_trial_to_keep_nauta_out_of_epg_scope(self):
        row = dict(self.row, sourceList="2.m3u")
        self.write_layout(row)
        with self.assertRaisesRegex(ValueError, "solo a Lista 1 y en prueba"):
            runner.apply_editor_nauta_channels(["#EXTM3U"], self.layout_path)

    def test_existing_matching_reference_is_not_duplicated_or_rewritten(self):
        self.write_layout()
        original = [
            "#EXTM3U",
            f'#EXTINF:-1 tvg-id="{self.channel_id}" group-title="Nauta",Original visible label',
            nauta_reference.reference("cat_4", self.name),
        ]
        before = list(original)

        self.assertFalse(runner.apply_editor_nauta_channels(original, self.layout_path))
        self.assertEqual(before, original)


if __name__ == "__main__":
    unittest.main()
