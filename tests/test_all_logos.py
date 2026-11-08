"""Todo canal publicado tiene logo («todo con logo es imperativo», 2026-11-07)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/"


class AllChannelsHaveLogoTest(unittest.TestCase):
    def test_published_lists(self):
        for name in ("1.m3u", "2.m3u", "m3u-externa.m3u", "m3u.m3u"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for line in re.findall(r"#EXTINF[^\n]*", text):
                m = re.search(r'tvg-logo="([^"]*)"', line)
                with self.subTest(lista=name, canal=line.rsplit(",", 1)[-1]):
                    self.assertTrue(m and m.group(1), "canal sin logo")
                    if m.group(1).startswith(BASE):
                        path = m.group(1)[len(BASE):].split("?", 1)[0]
                        self.assertTrue((ROOT / path).is_file(), m.group(1))


if __name__ == "__main__":
    unittest.main()
