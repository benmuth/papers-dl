from src.scihub import SciHub
from src.parse import parse_ids_from_text, id_patterns
import unittest
import os


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = "tests"

        cls.valid_id_types = id_patterns.keys()

    def test_parse_text(self):
        for file in test_document_ids:
            with open(os.path.join(TestParser.test_dir, file)) as f:
                file_content = f.read()
            for id_type in TestParser.valid_id_types:
                parsed_ids = parse_ids_from_text(file_content, id_type)
                expected_ids = test_document_ids[file].get(id_type)
                if not expected_ids:
                    continue

                parsed_ids = [id[1] for id in parsed_ids] # flatten
                for expected_id in expected_ids:
                    self.assertIn(
                        expected_id,
                        parsed_ids,
                        f"ID {expected_id} not found in {file} for ID type {id_type}",
                    )


class TestSciHub(unittest.TestCase):
    def setUp(self):
        self.scihub = SciHub()

    def test_scihub_up(self):
        """
        Tests to verify that `scihub.now.sh` is available
        """
        urls = self.scihub.available_base_url_list
        self.assertNotEqual(
            len(urls),
            0,
            "Failed to find Sci-Hub domains",
        )
        print(f"number of candidate urls: {len(urls)}")

    # TODO: This test is too flaky! Use it to make error handling more robust!
    # def test_fetch(self):
    #     with open("tests/identifiers.txt") as f:
    #         ids = f.read().splitlines()
    #         for id in ids:
    #             res = self.scihub.fetch(id)
    #             self.assertIsNotNone(res, f"Failed to fetch url from id {id}")


test_document_ids = {
    "identifiers.txt": {
        "url": ["https://www.cell.com/current-biology/fulltext/S0960-9822(19)31469-1"],
        "doi": ["10.1016/j.cub.2019.11.030"],
    },
    "sample-docs/bsp-tree.html": {
        "doi": ["10.1109/83.544569"],
        "issn": ["1057-7149", "1941-0042"],
    },
    "sample-docs/reyes-rendering.html": {
        "doi": ["10.1145/37402.37414"],
        "url": [
            "https://dl.acm.org/doi/10.1145/3603521.3604289",
            "https://doi.org/10.1145/3596711.3596742",
            "https://doi.org/10.1145/37402.37414",
        ],
    },
    "sample-docs/superscalar-cisc.html": {
        "doi": ["10.1109/HPCA.2006.1598111"],
        "issn": ["1530-0897", "2378-203X"],
    },
    "sample-docs/b-tree-techniques.html": {
        "doi": ["10.1561/1900000028"],
        "url": ["http://dx.doi.org/10.1561/1900000028"],
        "isbn": ["978-1-60198-482-1", "978-1-60198-483-8"],
    },
    "sample-docs/real-time-rendering.html": {
        "url": ["https://doi.org/10.1201/9781315365459"],
        "isbn": ["9781315365459"],
    },
}
