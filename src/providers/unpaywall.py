"""Resolve DOI PDFs through Unpaywall (requires UNPAYWALL_EMAIL)."""

import asyncio
import os
from urllib.parse import quote, unquote, urlsplit

import aiohttp
from loguru import logger

from parse.parse import parse_ids_from_text


async def get_urls(session, identifier):
    dois = parse_ids_from_text(unquote(identifier), ["doi"])
    if not dois:
        return []
    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not email:
        logger.info("Skipping Unpaywall: set UNPAYWALL_EMAIL to your contact email")
        return []
    doi = dois[0]["id"]
    try:
        async with session.get(
            "https://api.unpaywall.org/v2/" + quote(doi, safe="/"),
            params={"email": email},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                return []
            response.raise_for_status()
            data = await response.json()
        if (data.get("doi") or "").casefold() != doi.casefold():
            return []
        locations = [data.get("best_oa_location"), *(data.get("oa_locations") or [])]
        return list(
            dict.fromkeys(
                location["url_for_pdf"]
                for location in locations
                if location
                and location.get("url_for_pdf")
                and urlsplit(location["url_for_pdf"]).scheme in ("http", "https")
            )
        )
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover an Unpaywall PDF: {}", error)
        return []
