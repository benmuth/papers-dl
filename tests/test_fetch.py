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
        self.assertTrue(
            urls, "Failed to discover the mirror advertised by sci-hub.now.sh"
        )
