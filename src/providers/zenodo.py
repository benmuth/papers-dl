"""Discover PDFs from public Zenodo record/file metadata."""

import asyncio
import re
from urllib.parse import unquote, urlsplit

import aiohttp
from loguru import logger


async def get_urls(session, identifier):
    identifier = unquote(identifier.strip())
    doi = re.fullmatch(
        r"(?:https?://(?:dx\.)?doi\.org/)?10\.5281/zenodo\.(\d+)",
        identifier,
        re.IGNORECASE,
    )
    url = urlsplit(identifier)
    record = (
        re.fullmatch(r"/(?:api/)?records?/(\d+)/?", url.path)
        if url.hostname == "zenodo.org"
        else None
    )
    if not (doi or record):
        return []
    record_id = (doi or record).group(1)
    try:
        async with session.get(
            f"https://zenodo.org/api/records/{record_id}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
        if data.get("metadata", {}).get("access_right") != "open":
            return []
        return [
            file["links"]["self"]
            for file in data.get("files", [])
            if file.get("key", "").lower().endswith(".pdf")
            and file.get("links", {}).get("self")
        ]
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a Zenodo PDF: {}", error)
        return []
