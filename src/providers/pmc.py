"""Find article PDFs in NLM's public PMC Article Datasets."""

import asyncio
import hashlib
import re
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from parse.parse import parse_ids_from_text
from providers import publisher

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
DATASET = "https://pmc-oa-opendata.s3.amazonaws.com/"
TIMEOUT = aiohttp.ClientTimeout(total=30)
USER_AGENT = (
    "Mozilla/5.0 (compatible; papers-dl/0.0.25; +https://github.com/benmuth/papers-dl)"
)
S3_NAMESPACE = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


async def get_urls(session, identifier):
    identifier = unquote(identifier.strip())
    if identifier.startswith(("http://", "https://")):
        identifier = urlsplit(identifier).path.strip("/")
    pmcid = re.search(r"\bPMC\d+(?:\.\d+)?\b", identifier, re.IGNORECASE)
    dois = parse_ids_from_text(identifier, ["doi"])
    if pmcid:
        identifier = pmcid.group().upper()
        query = None
    elif dois:
        identifier = dois[0]["id"]
        query = f'DOI:"{identifier}"'
    elif identifier.isdigit():
        query = f"EXT_ID:{identifier} AND SRC:MED"
    else:
        return []

    logger.info("Searching PubMed Central: {}", identifier)
    try:
        if query:
            async with session.get(
                SEARCH,
                params={"query": query, "format": "json"},
                timeout=TIMEOUT,
            ) as response:
                response.raise_for_status()
                result = await response.json()
            records = result.get("resultList", {}).get("result", [])
            pmcids = [
                record["pmcid"]
                for record in records
                if record.get("pmcid")
                and (
                    record.get("doi", "").lower() == identifier.lower()
                    if dois
                    else str(record.get("pmid")) == identifier
                )
            ]
        else:
            pmcids = [identifier]

        urls = []
        for pmcid in dict.fromkeys(pmcids):
            if not re.fullmatch(r"PMC\d+(?:\.\d+)?", pmcid):
                continue
            if "." in pmcid:
                keys = [f"metadata/{pmcid}.json"]
            else:
                # List available metadata, not article files: supplements can
                # also be PDFs, and version 1 is not necessarily distributed.
                keys = []
                params = {"list-type": "2", "prefix": f"metadata/{pmcid}."}
                while True:
                    async with session.get(
                        DATASET, params=params, timeout=TIMEOUT
                    ) as response:
                        response.raise_for_status()
                        listing = ElementTree.fromstring(await response.read())
                    keys.extend(
                        key.text
                        for key in listing.findall("s3:Contents/s3:Key", S3_NAMESPACE)
                        if re.fullmatch(rf"metadata/{pmcid}\.\d+\.json", key.text or "")
                    )
                    token = listing.findtext(
                        "s3:NextContinuationToken", namespaces=S3_NAMESPACE
                    )
                    if not token:
                        break
                    params["continuation-token"] = token

            versions = []
            xml_versions = []
            for key in keys:
                async with session.get(DATASET + key, timeout=TIMEOUT) as response:
                    # Only licensed, publicly distributed versions are in S3.
                    if response.status == 404:
                        continue
                    response.raise_for_status()
                    # NLM's S3 JSON objects are served as binary/octet-stream.
                    metadata = await response.json(content_type=None)
                if metadata.get("pdf_url"):
                    versions.append(metadata)
                elif metadata.get("xml_url"):
                    xml_versions.append(metadata)
            # Prefer published articles to author manuscripts, then the newest
            # deposited version of that kind. Do not pick a supplemental PDF.
            versions.sort(
                key=lambda v: (v.get("is_manuscript", False), -int(v["version"]))
            )
            for metadata in versions:
                pdf_url = metadata["pdf_url"]
                url = urlsplit(pdf_url)
                if url.scheme == "s3" and url.netloc == "pmc-oa-opendata":
                    pdf_url = urlunsplit(
                        (
                            "https",
                            "pmc-oa-opendata.s3.amazonaws.com",
                            url.path,
                            url.query,
                            "",
                        )
                    )
                if urlsplit(pdf_url).scheme in ("https", "http"):
                    urls.append(pdf_url)
                    break
            if not versions and xml_versions and "." not in pmcid:
                # Manuscript PDFs may be absent from the public dataset while
                # its JATS XML advertises the article's browser-download PDF.
                # Read that self-uri directly: the HTML landing page can return
                # a browser challenge instead of its citation metadata.
                xml_versions.sort(
                    key=lambda v: (v.get("is_manuscript", False), -int(v["version"]))
                )
                for metadata in xml_versions:
                    xml_url = metadata["xml_url"]
                    if xml_url.startswith("s3://pmc-oa-opendata/"):
                        xml_url = DATASET + xml_url.removeprefix(
                            "s3://pmc-oa-opendata/"
                        )
                    async with session.get(xml_url, timeout=TIMEOUT) as response:
                        response.raise_for_status()
                        article = ElementTree.fromstring(await response.read())
                    pdf = article.find(
                        "./front/article-meta/self-uri[@content-type='pmc-pdf']"
                    )
                    filename = (
                        pdf.get("{http://www.w3.org/1999/xlink}href")
                        if pdf is not None
                        else None
                    )
                    if filename:
                        pdf_url = urljoin(
                            f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/",
                            filename,
                        )
                        if urlsplit(pdf_url).scheme in ("https", "http"):
                            urls.append(pdf_url)
                            break
            elif not versions and "." not in pmcid:
                urls.extend(
                    await publisher.get_urls(
                        session,
                        f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                        headers={
                            "User-Agent": session.headers.get("User-Agent", USER_AGENT)
                        },
                    )
                )
        return urls
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ValueError,
        ElementTree.ParseError,
    ) as error:
        logger.info("Couldn't find a PubMed Central PDF: {}", error)
        return []


async def complete_pdf_download(session, url, content, headers):
    """Complete PMC's automatic SHA-256 download proof, without executing JS.

    This is the public viewer's POW_CHALLENGE protocol, not a login or CAPTCHA.
    Bound the work and recognize it only on NCBI's PDF download endpoint.
    """
    if (
        url.scheme != "https"
        or url.host != "pmc.ncbi.nlm.nih.gov"
        or "/pdf/" not in url.path
    ):
        return None
    page = BeautifulSoup(content, "html.parser")
    script = "\n".join(tag.get_text() for tag in page.find_all("script", src=False))
    challenge = re.search(r'const POW_CHALLENGE = "([A-Za-z0-9_:.-]+)"', script)
    difficulty = re.search(r'const POW_DIFFICULTY = "([1-4])"', script)
    cookie = re.search(r'const POW_COOKIE_NAME = "(cloudpmc-viewer-pow)"', script)
    if not (challenge and difficulty and cookie):
        logger.info(
            "PMC PDF page is not a supported automatic proof "
            "(bytes={}, title={!r}, markers={}, challenge={}, difficulty={}, cookie_marker={})",
            len(content),
            page.title.get_text(strip=True)[:120] if page.title else "",
            [
                name
                for name in ("POW_CHALLENGE", "POW_DIFFICULTY", "POW_COOKIE_NAME")
                if name in script
            ],
            bool(challenge),
            difficulty.group(1) if difficulty else None,
            bool(cookie),
        )
        return None
    challenge = challenge.group(1)
    prefix = "0" * int(difficulty.group(1))

    def solve():
        for nonce in range(1 << 24):
            if (
                hashlib.sha256(f"{challenge}{nonce}".encode())
                .hexdigest()
                .startswith(prefix)
            ):
                return nonce
        return None

    nonce = await asyncio.to_thread(solve)
    if nonce is None:
        return None
    session.cookie_jar.update_cookies(
        {cookie.group(1): quote(f"{challenge},{nonce}", safe=":")}, response_url=url
    )
    async with session.get(url, timeout=TIMEOUT, headers=headers) as response:
        response.raise_for_status()
        content = await response.read()
        if not content.startswith(b"%PDF-"):
            page = BeautifulSoup(content, "html.parser")
            logger.info(
                "PMC automatic proof returned non-PDF content "
                "(HTTP {}, type={!r}, host={}, bytes={}, title={!r}, proof_page={})",
                response.status,
                response.headers.get("Content-Type", "")[:120],
                response.url.host,
                len(content),
                page.title.get_text(strip=True)[:120] if page.title else "",
                b"POW_CHALLENGE" in content,
            )
        return content, str(response.url)
