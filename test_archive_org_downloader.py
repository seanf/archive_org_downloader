import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

import archive_org_downloader

class TestArchiveOrgDownloader(unittest.TestCase):
    def test_extract_identifier_and_subdir(self):
        # Test download URL with subdirectory and percent encoding
        url1 = "https://archive.org/download/the-works-of-alexandre-dumas-alexandre-dumas/Old/Agatha%20Christie/Hercule%20Poirot%2028%20-%20The%20Witness%20for%20%28168%29/"
        ident, subdir = archive_org_downloader.extract_identifier_and_subdir(url1)
        self.assertEqual(ident, "the-works-of-alexandre-dumas-alexandre-dumas")
        self.assertEqual(subdir, "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)")

        # Test details URL
        url2 = "https://archive.org/details/example-item"
        ident, subdir = archive_org_downloader.extract_identifier_and_subdir(url2)
        self.assertEqual(ident, "example-item")
        self.assertEqual(subdir, "")

        # Test plain identifier
        url3 = "cdimage_collection_123"
        ident, subdir = archive_org_downloader.extract_identifier_and_subdir(url3)
        self.assertEqual(ident, "cdimage_collection_123")
        self.assertEqual(subdir, "")

        # Test legacy extract_identifier function
        self.assertEqual(archive_org_downloader.extract_identifier(url1), "the-works-of-alexandre-dumas-alexandre-dumas")

    def test_file_filtering(self):
        archive_files = [
            {"name": "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)/Hercule Poirot 28 - The Witness - Agatha Christie.epub"},
            {"name": "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)/Hercule Poirot 28 - The Witness - Agatha Christie.pdf"},
            {"name": "Old/Agatha Christie/Hercule Poirot 27/Hercule Poirot 27.epub"},
            {"name": "root_file.epub"}
        ]
        extensions = [".epub", ".pdf"]

        # Filter with subdir "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)"
        subdir = "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)"
        candidates = []
        for f in archive_files:
            name = f.get("name", "")
            if not archive_org_downloader.is_valid_file(name, extensions):
                continue
            if subdir:
                if name == subdir or name.startswith(subdir + "/") or name.lower() == subdir.lower() or name.lower().startswith(subdir.lower() + "/"):
                    candidates.append(f)
            else:
                candidates.append(f)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["name"], "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)/Hercule Poirot 28 - The Witness - Agatha Christie.epub")
        self.assertEqual(candidates[1]["name"], "Old/Agatha Christie/Hercule Poirot 28 - The Witness for (168)/Hercule Poirot 28 - The Witness - Agatha Christie.pdf")

if __name__ == "__main__":
    unittest.main()
