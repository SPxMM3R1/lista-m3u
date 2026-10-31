"""Logos livianos (2026-10-31).

La app dibuja los logos a unos 410 px como máximo: un PNG grande o pesado solo hace más
lenta la descarga. Fuera de ``logos/history/``: ninguno pasa de 64 KB, y si mide más de
512 px por lado debe pesar 40 KB o menos (PNG con paleta que crecería al achicarlo). Para
uno nuevo: lado máximo 512 px, ``optimize=True`` y, si sigue pesado, paleta de 256 colores
(ver ``contracts/logos-optimizados-20261031.json``).
"""
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_EDGE = 512
MAX_BYTES = 64 * 1024
MAX_BYTES_OVER_EDGE = 40 * 1024


def png_edge(path):
    """Lado mayor leído del encabezado IHDR (sin PIL: el CI no la instala)."""
    with path.open("rb") as handle:
        header = handle.read(24)
    width, height = struct.unpack(">II", header[16:24])
    return max(width, height)


class LogoSizeTest(unittest.TestCase):
    def test_published_logos_are_light(self):
        big = []
        for path in (ROOT / "logos").rglob("*.png"):
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith("logos/history/"):
                continue
            size = path.stat().st_size
            edge = png_edge(path)
            if size > MAX_BYTES or (edge > MAX_EDGE and size > MAX_BYTES_OVER_EDGE):
                big.append(f"{relative} {edge} px {size // 1024} KB")
        self.assertEqual([], big)


if __name__ == "__main__":
    unittest.main()
