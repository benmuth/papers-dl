"""Find PDF links advertised as open access by Europe PMC."""

import asyncio
import re
from urllib.parse import unquote, urlsplit

import aiohttp
from loguru import logger

from parse.parse import parse_ids_from_text
from providers.pmc import SEARCH, TIMEOUT


async def get_urls(session, identifier):
    identifier = unquote(identifier.strip())
    if identifier.startswith(("http://", "https://")):
        identifier = urlsplit(identifier).path.strip("/")
    pmcid = re.search(r"\bPMC\d+(?:\.\d+)?\b", identifier, re.IGNORECASE)
    dois = parse_ids_from_text(identifier, ["doi"])
    if pmcid:
        # Europe PMC's links don't identify a version. Leave explicit versions
        # to the PMC dataset provider instead of silently substituting one.
        if "." in pmcid.group():
            return []
        field, value = "pmcid", pmcid.group().upper()
        query = f"PMCID:{value}"
    elif dois:
        field, value = "doi", dois[0]["id"]
        query = f'DOI:"{value}"'
    elif identifier.isdigit():
        field, value = "id", identifier
        query = f"EXT_ID:{value} AND SRC:MED"
    else:
        return []
    try:
        async with session.get(
            SEARCH,
            params={"query": query, "format": "json", "resultType": "core"},
            timeout=TIMEOUT,
        ) as response:
            response.raise_for_status()
            data = await response.json()
        return list(
            dict.fromkeys(
                link["url"]
                for record in data.get("resultList", {}).get("result", [])
                if str(record.get(field) or "").casefold() == value.casefold()
                for link in (record.get("fullTextUrlList") or {}).get("fullTextUrl", [])
                if link.get("documentStyle") == "pdf"
                and link.get("availabilityCode") in ("OA", "F")
                and urlsplit(link.get("url", "")).scheme in ("http", "https")
            )
        )
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a Europe PMC PDF: {}", error)
        return []
