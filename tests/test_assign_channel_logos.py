import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "scripts"))

import assign_channel_logos  # noqa: E402
import build_site_data  # noqa: E402


class AssignChannelLogosTest(unittest.TestCase):
    def test_name_key_matches_editor_rules(self) -> None:
        key = assign_channel_logos.logo_name_key
        self.assertEqual("skysportsf1", key("SKY SPORTS F1 FHD (BACKUP)"))
        self.assertEqual("skysportsf1", key("logos/history/sky-sports-f1--7f3e7410ed.png"))
        self.assertEqual("skysportstennis", key("logos/sky-sports-tennis-logopedia.svg"))
        self.assertEqual("mtvhits", key("MTV HITS HD"))

    def test_suggestion_prefers_catalog_identity_then_current_then_history(self) -> None:
        catalog_logos = {
            "byId": {"SkySportsF1.uk": "logos/sky-sports-f1.png"},
            "byAlias": {"vavoo_DAZN F1|group:es": "logos/dazn-f1.png"},
        }
        logos = [
            "logos/history/sky-sports-main-event--88f04817b9.png",
            "logos/mtv-hits.png",
            "logos/history/mtv-hits--b961bb1b5a.png",
        ]
        suggest = assign_channel_logos.suggest_logo
        self.assertEqual("logos/sky-sports-f1.png", suggest(
            {"kind": "provider", "provider": "highfly", "catalogKey": "SkySportsF1.uk",
             "name": "SKY SPORTS F1"}, catalog_logos, logos))
        self.assertEqual("logos/dazn-f1.png", suggest(
            {"kind": "provider", "provider": "tvvoo",
             "catalogKey": "spain|vavoo_DAZN%20F1%7Cgroup%3Aes", "name": "DAZN F1"},
            catalog_logos, logos))
        self.assertEqual("logos/mtv-hits.png", suggest(
            {"kind": "provider", "provider": "tvvoo",
             "catalogKey": "france|vavoo_MTV%20HITS%20HD%7Cgroup%3Afr", "name": "MTV HITS HD"},
            catalog_logos, logos))
        self.assertEqual("logos/history/sky-sports-main-event--88f04817b9.png", suggest(
            {"kind": "provider", "provider": "highfly", "catalogKey": "SkySportsMainEvent.uk",
             "name": "SKY SPORTS MAIN EVENT"}, catalog_logos, logos))

    def test_catalog_logos_split_local_and_remote_by_alias(self) -> None:
        text = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="DAZNF1.es@TvVoo" tvg-logo="https://raw.githubusercontent.com/'
            'SPxMM3R1/lista-m3u/main/logos/dazn-f1.png" x-resolver-ids="vavoo_DAZN%20F1%7Cgroup%3Aes",DAZN F1\n'
            "http://x\n"
            '#EXTINF:-1 tvg-id="Vavoo.de.MTV@TvVoo" tvg-logo="https://raw.githubusercontent.com/'
            'tv-logo/tv-logos/main/countries/germany/mtv-de.png" x-resolver-ids="vavoo_MTV%7Cgroup%3Ade",MTV\n'
            "http://y\n"
        )
        result = build_site_data.parse_catalog_logos(text)
        self.assertEqual("logos/dazn-f1.png", result["byId"]["DAZNF1.es@TvVoo"])
        self.assertEqual("logos/dazn-f1.png", result["byAlias"]["vavoo_DAZN F1|group:es"])
        self.assertIn("mtv-de.png", result["remoteByAlias"]["vavoo_MTV|group:de"])
        self.assertNotIn("Vavoo.de.MTV@TvVoo", result["byId"])

    def test_only_real_tv_logo_images_are_accepted(self) -> None:
        self.assertEqual(".png", assign_channel_logos.image_extension(b"\x89PNG\r\n\x1a\n...."))
        self.assertIsNone(assign_channel_logos.image_extension(b"<html>no</html>"))


if __name__ == "__main__":
    unittest.main()
