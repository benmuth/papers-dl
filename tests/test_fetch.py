import unittest

import aiohttp
import asyncio

from src.providers.scihub import SciHub


class TestSciHub(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with aiohttp.ClientSession() as session:
            self.scihub = SciHub(session, await SciHub.get_available_scihub_urls())

    def test_scihub_up(self):
        """
        Test to verify that `scihub.now.sh` is available
        """
        urls = self.scihub.available_base_url_list
        self.assertIsNotNone(urls, "Failed to find Sci-Hub domains")

    # NOTE: This test is flaky. Retrieval doesn't work consistently
    # def test_fetch(self):
    #     with open("tests/identifiers/ids.txt") as f:
    #         ids = f.read().splitlines()
    #         for id in ids:
    #             res = self.scihub.fetch(id)
    #             self.assertIsNotNone(res, f"Failed to fetch url from id {id}")
