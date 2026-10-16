"""Discover versioned preprint PDFs using the bioRxiv/medRxiv metadata API."""

import asyncio
import re
from urllib.parse import quote, unquote, urlsplit

import aiohttp
from loguru import logger

from parse.parse import parse_ids_from_text


async def get_urls(session, identifier, server="biorxiv"):
    identifier = unquote(identifier.strip())
    url = urlsplit(identifier)
    version = None
    if url.hostname and url.hostname.removeprefix("www.") == f"{server}.org":
        match = re.search(
            r"(10\.(?:1101|64898)/.+?)(?:v(\d+))?(?:\.full(?:\.pdf)?|\.abstract)?/?$",
            url.path,
        )
        if not match:
            return []
        doi, version = match.groups()
    else:
        dois = parse_ids_from_text(identifier, ["doi"])
        if not dois:
            return []
        doi = dois[0]["id"]
    headers = {
        "User-Agent": session.headers.get(
            "User-Agent", "papers-dl (https://github.com/benmuth/papers-dl)"
        )
    }
    try:
        # Published DOIs can map to preprints through the documented pubs API.
        if not doi.startswith(("10.1101/", "10.64898/")):
            async with session.get(
                f"https://api.biorxiv.org/pubs/{server}/{quote(doi, safe='/')}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json()
            matches = [
                item
                for item in data.get("collection", [])
                if (item.get("published_doi") or "").casefold() == doi.casefold()
                and (item.get("preprint_platform") or "").casefold() == server
            ]
            if not matches:
                return []
            doi = matches[0].get("preprint_doi") or matches[0].get("biorxiv_doi")
            if not doi:
                return []
        async with session.get(
            f"https://api.biorxiv.org/details/{server}/{quote(doi, safe='/')}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
        versions = [
            int(item["version"])
            for item in data.get("collection", [])
            if (item.get("doi") or "").casefold() == doi.casefold()
            and (item.get("server") or "").casefold() == server
            and str(item.get("version", "")).isdigit()
            and (version is None or str(item["version"]) == version)
        ]
        if not versions:
            return []
        return [f"https://www.{server}.org/content/{doi}v{max(versions)}.full.pdf"]
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a {} PDF: {}", server, error)
        return []
