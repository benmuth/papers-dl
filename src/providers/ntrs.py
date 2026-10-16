"""Find publicly downloadable reports using NASA NTRS citation metadata."""

import asyncio
import re
from urllib.parse import urljoin, urlsplit

import aiohttp
from loguru import logger


async def get_urls(session, identifier):
    identifier = identifier.strip()
    url = urlsplit(identifier)
    citation = (
        re.fullmatch(r"/(?:api/)?citations/(\d+)/?", url.path)
        if url.hostname == "ntrs.nasa.gov"
        else re.fullmatch(r"ntrs:(\d+)", identifier, re.IGNORECASE)
    )
    if not citation:
        return []
    try:
        async with session.get(
            f"https://ntrs.nasa.gov/api/citations/{citation.group(1)}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
        if data.get("distribution") != "PUBLIC":
            return []
        return [
            urljoin("https://ntrs.nasa.gov/", file["links"]["pdf"])
            for file in data.get("downloads", [])
            if not file.get("draft") and file.get("links", {}).get("pdf")
        ]
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a NASA NTRS PDF: {}", error)
        return []
