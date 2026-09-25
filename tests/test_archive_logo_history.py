from __future__ import annotations

import unittest
from pathlib import Path

from tools import archive_logo_history


class ArchiveLogoHistoryTests(unittest.TestCase):
    def test_object_parser_keeps_supported_files_and_ignores_generated_archive(self) -> None:
        objects = "\n".join(
            (
                f"{'a' * 40} logos/sky-sports.svg",
                f"{'b' * 40} logos/sky-sports.png",
                f"{'c' * 40} logos/history/sky-sports--{'c' * 10}.png",
                f"{'d' * 40} logos/notes.txt",
            )
        )

        self.assertEqual(
            archive_logo_history.parse_logo_objects(objects),
            {"a" * 40: "logos/sky-sports.svg", "b" * 40: "logos/sky-sports.png"},
        )

    def test_current_tree_ignores_history_and_non_logo_files(self) -> None:
        tree = "\n".join(
            (
                f"100644 blob {'a' * 40}\tlogos/sky-sports.svg",
                f"100644 blob {'b' * 40}\tlogos/history/sky-sports--{'b' * 10}.png",
                f"100644 blob {'c' * 40}\tlogos/README.md",
            )
        )

        self.assertEqual(archive_logo_history.parse_current_logo_blobs(tree), {"a" * 40})

    def test_archive_name_is_descriptive_deterministic_and_safe(self) -> None:
        path = archive_logo_history.archive_name("logos/Sky Sports/Main Event.svg", "a" * 40)

        self.assertEqual(path, Path("logos/history/Main-Event--aaaaaaaaaa.svg"))

    def test_archive_name_rejects_unknown_extensions_and_invalid_blob_ids(self) -> None:
        with self.assertRaises(ValueError):
            archive_logo_history.archive_name("logos/logo.gif", "a" * 40)
        with self.assertRaises(ValueError):
            archive_logo_history.archive_name("logos/logo.svg", "not-a-git-blob")


if __name__ == "__main__":
    unittest.main()
