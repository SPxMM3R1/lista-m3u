"""Documentos de traspaso cortos (2026-10-31).

Los agentes recortan los archivos largos al leerlos: si AGENTS.md o ESTADO.md crecen sin
límite, el traspaso entre proveedores de IA pierde reglas. Lo antiguo va a ``docs/``.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"AGENTS.md": 25_000, "ESTADO.md": 60_000}
DOCS = ("decisiones-por-canal.md", "epg.md", "respaldos.md", "historial-operativo.md", "estado-anterior.md")


class DocsSizeTest(unittest.TestCase):
    def test_handoff_documents_stay_short(self):
        for name, limit in LIMITS.items():
            size = (ROOT / name).stat().st_size
            self.assertLessEqual(size, limit, f"{name} pesa {size} bytes: mueve lo antiguo a docs/ (ver AGENTS.md, protocolo)")

    def test_agents_points_to_every_doc(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for doc in DOCS:
            self.assertTrue((ROOT / "docs" / doc).is_file(), doc)
            self.assertIn(f"docs/{doc}", agents)


if __name__ == "__main__":
    unittest.main()
