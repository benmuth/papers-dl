from src.scihub import SciHub
from src.parse import parse_ids_from_text
import unittest
import os


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = "tests"

        cls.valid_id_types = ("url", "pmid", "doi")

        cls.expected_ids = {
            "identifiers.txt": [
                "https://www.cell.com/current-biology/fulltext/S0960-9822(19)31469-1",
                "10.1016/j.cub.2019.11.030",
            ],
            "sample-docs/superscalar-cisc.html": ["10.1109/HPCA.2006.1598111"],
        }

        for expected_ids in cls.expected_ids.values():
            expected_ids.sort()

    def test_parse_text(self):
        for file in TestParser.expected_ids:
            with open(os.path.join(TestParser.test_dir, file)) as f:
                content = f.read()
                self.parser_test(content, TestParser.expected_ids[file])

    def parser_test(self, content, expected_ids):
        parsed_ids = []
        for id_type in TestParser.valid_id_types:
            ids = parse_ids_from_text(content, id_type)
            if ids:
                parsed_ids.extend(ids)

        parsed_ids.sort()

        for i in range(len(expected_ids)):
            self.assertEqual(expected_ids[i], parsed_ids[i])


class TestSciHub(unittest.TestCase):
    def setUp(self):
        self.scihub = SciHub()

    def test_scihub_up(self):
        """
        Tests to verify that `scihub.now.sh` is working
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
