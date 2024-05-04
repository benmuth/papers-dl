from src.scihub import SciHub
from src.papers_dl import DEFAULT_USER_AGENT
import unittest

class TestSciHub(unittest.TestCase):
    def setUp(self):
        self.scihub = SciHub(DEFAULT_USER_AGENT)

    def test_scihub_up(self):
        """
        Test to verify that `scihub.now.sh` is available
        """
        urls = self.scihub.available_base_url_list
        self.assertIsNotNone(urls, "Failed to find Sci-Hub domains")
        print(f"number of candidate urls: {len(urls)}")

    # NOTE: This test is flaky. Retrieval doesn't work consistently
    def test_fetch(self):
        with open("tests/identifiers/ids.txt") as f:
            ids = f.read().splitlines()
            for id in ids:
                res = self.scihub.fetch(id)
                self.assertIsNotNone(res, f"Failed to fetch url from id {id}")
