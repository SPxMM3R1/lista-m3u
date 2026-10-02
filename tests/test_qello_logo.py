"""Regresiones del cambio de color aprobado, sin redibujar el logo Qello."""

import hashlib
import json
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "logos" / "qello.svg"
PNG = ROOT / "logos" / "qello.png"
NS = {"svg": "http://www.w3.org/2000/svg"}


class QelloLogoTests(unittest.TestCase):
    def test_white_letters_and_original_cyan(self):
        root = ET.parse(SVG).getroot()
        group = root.find("svg:g[@id='Icone']", NS)
        self.assertIsNotNone(group)
        self.assertEqual(group.get("fill"), "#FFFFFF")
        self.assertIn(".st0{fill:#03A4D9;}", root.find("svg:style", NS).text)
        self.assertIsNone(root.find(".//svg:rect", NS))

    def test_original_geometry_is_unchanged(self):
        root = ET.parse(SVG).getroot()
        shapes = [
            (element.tag.split("}")[-1], {
                key: " ".join(value.split())
                for key, value in sorted(element.attrib.items())
                if key in ("d", "points", "class")
            })
            for element in root.iter()
            if element.tag.split("}")[-1] in ("path", "polygon")
        ]
        self.assertEqual(len(shapes), 24)
        digest = hashlib.sha256(json.dumps(
            shapes, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        self.assertEqual(digest, "d4066422b7cc40f1b683d6265d0a85c0f11700e354c6be4cedaccaac86e353b2")
        self.assertEqual(root.get("viewBox"), "0 0 500 211.8")

    def test_png_keeps_size_and_alpha_channel(self):
        with PNG.open("rb") as image:
            header = image.read(33)
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(header[12:16], b"IHDR")
        width, height, depth, color, _, _, _ = struct.unpack(
            ">IIBBBBB", header[16:29]
        )
        self.assertEqual((width, height), (1000, 424))
        self.assertEqual((depth, color), (8, 6))  # RGBA, not an opaque mockup.


if __name__ == "__main__":
    unittest.main()
