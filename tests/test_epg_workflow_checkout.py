from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EpgWorkflowCheckoutTests(unittest.TestCase):
    def test_every_epg_job_checks_out_current_main(self) -> None:
        lines = (ROOT / ".github" / "workflows" / "update-epg.yml").read_text(
            encoding="utf-8"
        ).splitlines()
        checkouts = [
            index
            for index, line in enumerate(lines)
            if line.strip() == "- uses: actions/checkout@v4"
        ]

        self.assertEqual(len(checkouts), 3)
        for index in checkouts:
            self.assertEqual(lines[index + 1].strip(), "with:")
            self.assertEqual(lines[index + 2].strip(), "ref: main")


if __name__ == "__main__":
    unittest.main()
