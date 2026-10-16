"""Resolve HAL deposits and DOIs to their public main document."""

import asyncio
import json
import re
from urllib.parse import unquote, urljoin, urlsplit

import aiohttp
from loguru import logger

from parse.parse import parse_ids_from_text


async def get_urls(session, identifier):
    identifier = unquote(identifier.strip())
    url = urlsplit(identifier)
    if (
        url.scheme in ("http", "https")
        and url.hostname
        and (
            url.hostname == "hal.science"
            or url.hostname.endswith(".hal.science")
            or url.hostname.endswith(".archives-ouvertes.fr")
        )
    ):
        identifier = url.path.strip("/").split("/")[0]
    record = re.fullmatch(
        r"((?:hal(?:shs)?|tel|inria)-\d+)(?:v(\d+))?", identifier, re.IGNORECASE
    )
    dois = parse_ids_from_text(identifier, ["doi"])
    if record:
        query = "halId_s:" + json.dumps(record.group(1).lower())
    elif dois:
        query = "doiId_s:" + json.dumps(dois[0]["id"])
    else:
        return []
    try:
        async with session.get(
            "https://api.archives-ouvertes.fr/search/",
            params={
                "q": query,
                "fl": "halId_s,version_i,doiId_s,uri_s,fileMain_s",
                "sort": "version_i desc",
                "wt": "json",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            data = await response.json()
        for item in data.get("response", {}).get("docs", []):
            if record:
                if item.get("halId_s", "").lower() != record.group(1).lower():
                    continue
            elif item.get("doiId_s", "").lower() != dois[0]["id"].lower():
                continue
            if item.get("fileMain_s"):
                if record and record.group(2):
                    # Search indexes the current version. HAL's canonical
                    # version/document route also serves older public versions.
                    return [
                        urljoin(
                            item["uri_s"],
                            f"/{record.group(1).lower()}v{record.group(2)}/document",
                        )
                    ]
                return [item["fileMain_s"]]
        return []
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a HAL PDF: {}", error)
        return []
