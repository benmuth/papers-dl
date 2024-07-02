import unittest

import aiohttp
import asyncio

from src.providers.scihub import get_available_scihub_urls


class TestSciHub(unittest.IsolatedAsyncioTestCase):
    async def test_scihub_up(self):
        """
        Test to verify that `scihub.now.sh` is available
        """
        urls = await get_available_scihub_urls()
        self.assertIsNotNone(urls, "Failed to find Sci-Hub domains")
