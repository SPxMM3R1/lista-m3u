import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import update_m3u


class TrialChannelsTest(unittest.TestCase):
    def write(self, name: str, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_manifest_reads_trial_ids_and_external_switch(self) -> None:
        path = self.write("presentation-overrides.json", json.dumps({
            "schema": 1,
            "orders": {},
            "trial_m3u": ["TVN.cl@tlink", "CDO.cl@tlink"],
            "external_list_disabled": True,
        }))
        overrides = update_m3u.load_presentation_overrides(path)
        self.assertEqual(
            frozenset({"TVN.cl@tlink", "CDO.cl@tlink"}),
            update_m3u.trial_m3u_ids(overrides),
        )
        self.assertTrue(update_m3u.external_list_disabled(overrides))

    def test_manifest_defaults_keep_current_behaviour(self) -> None:
        path = self.write("presentation-overrides.json", json.dumps({"schema": 1, "orders": {}}))
        overrides = update_m3u.load_presentation_overrides(path)
        self.assertEqual(frozenset(), update_m3u.trial_m3u_ids(overrides))
        self.assertFalse(update_m3u.external_list_disabled(overrides))

    def test_manifest_rejects_a_url_as_trial_id(self) -> None:
        path = self.write("presentation-overrides.json", json.dumps({
            "schema": 1, "orders": {}, "trial_m3u": ["https://example.invalid/a.m3u8"],
        }))
        with self.assertRaises(ValueError):
            update_m3u.load_presentation_overrides(path)

    def test_trial_channels_are_outside_the_epg_scope(self) -> None:
        playlist = self.write("m3u.m3u", "\n".join([
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="0104" tvg-name="TVN" group-title="Nacionales",TVN',
            "https://example.invalid/tvn.m3u8",
            '#EXTINF:-1 tvg-id="TVN.cl@tlink" tvg-name="TVN [tlink]" group-title="Nacionales",TVN [tlink]',
            "https://example.invalid/tlink.m3u8",
        ]) + "\n")
        with mock.patch.object(update_m3u, "DEFAULT_PLAYLIST", playlist), \
                mock.patch.object(update_m3u, "trial_m3u_ids", return_value=frozenset({"TVN.cl@tlink"})):
            channels = update_m3u.main_playlist_channels()
        self.assertEqual(["0104"], [channel.tvg_id for channel in channels])


if __name__ == "__main__":
    unittest.main()
