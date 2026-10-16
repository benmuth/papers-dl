import asyncio
import enum
from urllib.parse import quote, urljoin, urlsplit

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from parse.parse import find_pdf_url

# URL-DIRECT - openly accessible paper
# URL-NON-DIRECT - pay-walled paper
# PMID - PubMed ID
# DOI - digital object identifier
IDClass = enum.Enum("identifier", ["URL-DIRECT", "URL-NON-DIRECT", "PMID", "DOI"])

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"


class IdentifierNotFoundError(Exception):
    pass


async def get_available_scihub_urls() -> list[str]:
    """Discover mirrors from the directory's links or its current redirects."""
    directory_hosts = {"sci-hub.now.sh", "sci-hub.vercel.app"}
    urls = []
    url = "https://sci-hub.now.sh/"
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            visited = set()
            while url not in visited and len(visited) < 10:
                visited.add(url)
                host = urlsplit(url).hostname or ""
                if (
                    host.startswith(("sci-hub.", "scihub."))
                    and host not in directory_hosts
                ):
                    # Retain the advertised mirror even if it is unreachable:
                    # discovery and successful paper retrieval are distinct.
                    urls.append(url)
                async with session.get(url, allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        url = urljoin(url, response.headers["Location"])
                        if urlsplit(url).scheme not in ("http", "https"):
                            break
                        continue
                    response.raise_for_status()
                    page = BeautifulSoup(await response.text(), "html.parser")
                    for link in page.find_all("a", href=True):
                        candidate = urljoin(url, link["href"])
                        parsed = urlsplit(candidate)
                        if (
                            parsed.scheme in ("http", "https")
                            and (parsed.hostname or "").startswith(
                                ("sci-hub.", "scihub.")
                            )
                            and parsed.hostname not in directory_hosts
                        ):
                            urls.append(candidate)
                    break
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError) as error:
        logger.info("Couldn't read Sci-Hub directory: {}", error)
    return list(dict.fromkeys(urls))


async def get_direct_urls(
    session,
    identifier: str,
    base_urls: list[str] | None = None,
) -> list[str]:
    """
    Finds the direct source url for a given identifier.
    """

    if classify(identifier) == IDClass["URL-DIRECT"]:
        return [identifier]
    if base_urls is None:
        base_urls = await get_available_scihub_urls()
    logger.info("searching Sci-Hub urls: {}", base_urls)

    async def get_wrapper(base_url):
        # A publisher URL is a lookup value, never a replacement for the mirror.
        url = base_url.rstrip("/") + "/" + quote(identifier, safe="/")
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                content = await response.read()
                if content.startswith(b"%PDF-"):
                    return str(response.url)
                path = find_pdf_url(content)
                if isinstance(path, list):
                    path = path[0] if path else None
                if isinstance(path, str):
                    direct_url = urljoin(str(response.url), path)
                    if urlsplit(direct_url).scheme in ("http", "https"):
                        return direct_url
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            logger.info("Couldn't read Sci-Hub mirror {}: {}", base_url, error)
        return None

    urls = await asyncio.gather(*(get_wrapper(url) for url in base_urls))
    return list(dict.fromkeys(url for url in urls if url))


def classify(identifier) -> IDClass:
    """
    Classify the type of identifier:
    url-direct - openly accessible paper
    url-non-direct - pay-walled paper
    pmid - PubMed ID
    doi - digital object identifier
    """
    if identifier.startswith("http") or identifier.startswith("https"):
        if identifier.endswith("pdf"):
            return IDClass["URL-DIRECT"]
        else:
            return IDClass["URL-NON-DIRECT"]
    elif identifier.isdigit():
        return IDClass["PMID"]
    else:
        return IDClass["DOI"]
