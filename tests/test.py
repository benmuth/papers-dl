from src.scihub import SciHub
from src.parse import parse_ids
import unittest

# TODO: get mock assets for tests to avoid problems
# with captchas

test_dir = "tests/"


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid_id_types = ("url", "pmid", "doi")

        with open(test_dir + "identifiers.txt") as f:
            cls.text_content = f.read()

        with open(test_dir + "identifiers.html") as f:
            cls.html_content = f.read()

        cls.expected_ids = {
            "text": [
                "https://www.cell.com/current-biology/fulltext/S0960-9822(19)31469-1",
                "10.1016/j.cub.2019.11.030",
            ],
            "html": [],
        }

        for expected_ids in cls.expected_ids.values():
            expected_ids.sort()

    def test_parse_text(self):
        self.parser_test(TestParser.html_content, TestParser.expected_ids["text"])

    def test_parse_html(self):
        self.parser_test(TestParser.html_content, TestParser.expected_ids["html"])

    def parser_test(self, content, expected_ids):
        parsed_ids = []
        for id_type in TestParser.valid_id_types:
            ids = parse_ids(content, id_type)
            if ids:
                for id in ids:
                    parsed_ids.append(id)

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

    def test_fetch(self):
        with open("tests/dois.txt") as f:
            ids = f.read().splitlines()
            for id in ids:
                res = self.scihub.fetch(id)
                self.assertIsNotNone(res, f"Failed to fetch url from id {id}")
