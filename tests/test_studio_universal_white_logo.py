import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WHITE_LOGO = "logos/catalogue/studiouniversallatinamerica-white.png"
ACTIVE_ROWS = {
    "PublicDirect.8b604de41196cd4fe991d551": "1.m3u",
    "Nauta.b9df5eea317035bd5bda31cf@Nauta": "2.m3u",
    # PublicDirect.52f6bff3… (Studio Universal HD 45.171.64.30) pasó a backups.json el
    # 2026-10-25 como respaldo del Studio Universal de Lista 1 (misma señal por audio).
}


def png_size(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"Not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


class StudioUniversalWhiteLogoTest(unittest.TestCase):
    def test_white_variant_preserves_original_canvas_size(self):
        source = ROOT / "logos/catalogue/studiouniversallatinamerica-us.png"
        white = ROOT / WHITE_LOGO
        self.assertTrue(white.is_file())
        self.assertEqual(png_size(source), png_size(white))

    def test_all_active_studio_universal_rows_use_white_variant(self):
        layout = json.loads((ROOT / "data/channel-editor-layout.json").read_text(encoding="utf-8"))
        rows = {row["tvgId"]: row for row in layout["channels"] if row.get("tvgId")}
        presentation = json.loads((ROOT / "presentation-overrides.json").read_text(encoding="utf-8"))
        logo_url = (
            "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/"
            "logos/catalogue/studiouniversallatinamerica-white.png"
        )

        for channel_id, source_list in ACTIVE_ROWS.items():
            with self.subTest(channel=channel_id):
                row = rows[channel_id]
                self.assertEqual("active", row["state"])
                self.assertEqual(source_list, row["sourceList"])
                self.assertEqual(WHITE_LOGO, row["logoPath"])
                self.assertEqual(WHITE_LOGO, row.get("logoOverride", WHITE_LOGO))
                self.assertEqual(WHITE_LOGO, presentation["logos"][channel_id])

                extinf = next(
                    (
                        line
                        for line in (ROOT / source_list).read_text(encoding="utf-8").splitlines()
                        if line.startswith("#EXTINF") and f'tvg-id="{channel_id}"' in line
                    ),
                    None,
                )
                self.assertIsNotNone(extinf)
                self.assertIn(f'tvg-logo="{logo_url}"', extinf)


if __name__ == "__main__":
    unittest.main()
