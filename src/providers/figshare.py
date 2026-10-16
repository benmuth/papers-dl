"""Discover PDFs through Figshare's public API, including institutional portals."""

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
        re.fullmatch(r"/(?:v2/)?articles/(?:[^/]+/)*?(\d+)(?:/(\d+))?/?", url.path)
        if url.scheme in ("http", "https")
        else None
    )
    dois = parse_ids_from_text(identifier, ["doi"])
    if not (record or dois):
        return []
    try:
        if record:
            record_id, version = record.groups()
        else:
            doi = dois[0]["id"]
            async with session.get(
                "https://api.figshare.com/v2/articles",
                params={"doi": doi},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                matches = await response.json()
            matches = [
                item for item in matches if item.get("doi", "").lower() == doi.lower()
            ]
            if not matches:
                return []
            record_id = str(matches[0]["id"])
            version_match = re.search(r"\.v(\d+)$", doi)
            version = version_match.group(1) if version_match else None
        endpoint = f"https://api.figshare.com/v2/articles/{record_id}"
        if version:
            endpoint += f"/versions/{version}"
        async with session.get(
            endpoint, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            response.raise_for_status()
            data = await response.json()
        # Institutional portals can use custom domains. Validate their identity
        # against the API record instead of treating every /articles URL as Figshare.
        if record and url.hostname not in ("figshare.com", "api.figshare.com"):
            if url.hostname != urlsplit(data.get("url_public_html", "")).hostname:
                return []
        if data.get("is_embargoed") or data.get("is_confidential"):
            return []
        return [
            file["download_url"]
            for file in data.get("files", [])
            if file.get("download_url")
            and (
                file.get("mimetype") == "application/pdf"
                or file.get("name", "").lower().endswith(".pdf")
            )
        ]
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a Figshare PDF: {}", error)
        return []
