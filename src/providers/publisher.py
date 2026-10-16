"""Discover PDFs advertised by DOI destinations and publisher landing pages."""

import asyncio
import re
from urllib.parse import quote, urljoin, urlsplit

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from parse.parse import find_pdf_url

TIMEOUT = aiohttp.ClientTimeout(total=30)


async def get_urls(session, identifier, headers=None):
    identifier = identifier.strip()
    if urlsplit(identifier).scheme in ("http", "https"):
        url = identifier
    elif re.match(r"^10\.\d{4,9}/\S+$", identifier):
        url = "https://doi.org/" + quote(identifier, safe="/")
    else:
        return []

    logger.info("Searching publisher: {}", url)
    try:
        async with session.get(url, timeout=TIMEOUT, headers=headers) as response:
            response.raise_for_status()
            content = await response.read()
            if content.startswith(b"%PDF-"):
                return [str(response.url)]
            page_url = str(response.url)
        page = BeautifulSoup(content, "html.parser")
        base = page.find("base", href=True)
        if base:
            page_url = urljoin(page_url, base["href"])
        candidates = [
            tag.get("content")
            for tag in page.find_all(
                "meta",
                attrs={"name": re.compile(r"^citation_pdf_url$", re.IGNORECASE)},
            )
        ]
        candidates.extend(
            tag.get("href")
            for tag in page.find_all("link", href=True)
            if tag.get("type", "").split(";")[0].lower() == "application/pdf"
        )
        candidates.append(find_pdf_url(content))
        urls = []
        for candidate in candidates:
            if candidate:
                pdf_url = urljoin(page_url, candidate.strip())
                if (
                    urlsplit(pdf_url).scheme in ("http", "https")
                    and pdf_url not in urls
                ):
                    urls.append(pdf_url)
        if not urls:
            logger.info(
                "No publisher PDF metadata (host={}, HTTP {}, type={!r}, bytes={}, title={!r})",
                urlsplit(page_url).hostname,
                response.status,
                response.headers.get("Content-Type", "")[:120],
                len(content),
                page.title.get_text(strip=True)[:120] if page.title else "",
            )
        return urls
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.info("Couldn't discover a publisher PDF: {}", error)
        return []
