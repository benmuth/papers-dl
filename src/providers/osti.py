"""Find public full-text reports through the DOE OSTI records API."""

import asyncio
import re
from urllib.parse import unquote, urlsplit

import aiohttp
from loguru import logger

from parse.parse import parse_ids_from_text


async def get_urls(session, identifier):
    identifier = unquote(identifier.strip())
    url = urlsplit(identifier)
    record = (
        re.match(r"/(?:biblio|servlets/purl|api/v1/records)/(\d+)(?:/|$)", url.path)
        if url.hostname in ("osti.gov", "www.osti.gov")
        else re.fullmatch(r"osti:(\d+)", identifier, re.IGNORECASE)
    )
    dois = parse_ids_from_text(identifier, ["doi"])
    if not (record or dois):
        return []
    endpoint = "https://www.osti.gov/api/v1/records"
    params = {}
    if record:
        endpoint += "/" + record.group(1)
    else:
        params["doi"] = dois[0]["id"]
    try:
        async with session.get(
            endpoint,
            params=params,
            headers={"Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            records = await response.json()
        return [
            link["href"]
            for item in records
            if record or item.get("doi", "").lower() == dois[0]["id"].lower()
            for link in item.get("links", [])
            if link.get("rel") == "fulltext" and link.get("href")
        ]
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover an OSTI PDF: {}", error)
        return []
