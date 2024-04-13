from src.scihub import SciHub
import unittest
# import requests


class TestSciHub(unittest.TestCase):
    def setUp(self):
        self.scihub = SciHub()

    def test_scihub_up(self):
        """
        Tests to verify that `scihub.now.sh` is working
        """
        self.assertNotEqual(
            len(self.scihub.available_base_url_list),
            0,
            "Failed to find Sci-Hub domains",
        )
        for url in self.scihub.available_base_url_list:
            self.assertTrue("sci" in url, f"Found URL that may be irrelevant: {url}")
