from src.scihub import SciHub
import unittest

# TODO: get mock assets for tests to avoid problems
# with captchas


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
        with open('tests/dois.txt') as f:
            ids = f.read().splitlines()
            for id in ids:
                res = self.scihub.fetch(id)
                self.assertIsNotNone(res, f"Failed to fetch url from id {id}")
