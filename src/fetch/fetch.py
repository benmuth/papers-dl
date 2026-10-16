import asyncio
import hashlib
import json
import os
from typing import Iterable
from urllib.parse import urlsplit

import aiohttp
import pdf2doi
from bs4 import BeautifulSoup
from loguru import logger
from parse.parse import parse_ids_from_text

from providers import (
    arxiv,
    biorxiv,
    medrxiv,
    unpaywall,
    europepmc,
    figshare,
    hal,
    ntrs,
    osti,
    pmc,
    publisher,
    scidb,
    scihub,
    zenodo,
)

all_providers = [
    "scihub",
    "unpaywall",
    "pmc",
    "europepmc",
    "biorxiv",
    "medrxiv",
    "publisher",
    "zenodo",
    "figshare",
    "ntrs",
    "osti",
    "hal",
    "scidb",
    "arxiv",
]


def match_available_providers(
    providers, available_providers: Iterable[str] | None = None
) -> list[str]:
    "Find the providers that are included in available_providers"
    if not available_providers:
        available_providers = all_providers
    matching_providers = []
    for provider in providers:
        if provider in available_providers:
            matching_providers.append(provider)
            continue
        for available_provider in available_providers:
            # a user-supplied provider might be a substring of a supported
            # provider (e.g. sci-hub.ee instead of https://sci-hub.ee)
            if provider in available_provider:
                matching_providers.append(available_provider)
    return matching_providers


async def get_urls(session, identifier, providers):
    urls = []
    if providers == "all":
        providers = all_providers
    else:
        providers = [provider.strip() for provider in providers.split(",")]
    logger.info(f"given providers: {providers}")

    matching_providers = match_available_providers(providers)
    logger.info(f"matching providers: {matching_providers}")
    for mp in matching_providers:
        if mp == "unpaywall":
            urls.extend(await unpaywall.get_urls(session, identifier))
        if mp == "europepmc":
            urls.extend(await europepmc.get_urls(session, identifier))
        if mp == "biorxiv":
            urls.extend(await biorxiv.get_urls(session, identifier))
        if mp == "medrxiv":
            urls.extend(await medrxiv.get_urls(session, identifier))
        if mp == "publisher":
            urls.extend(await publisher.get_urls(session, identifier))
        if mp == "pmc":
            urls.extend(await pmc.get_urls(session, identifier))
        if mp == "zenodo":
            urls.extend(await zenodo.get_urls(session, identifier))
        if mp == "figshare":
            urls.extend(await figshare.get_urls(session, identifier))
        if mp == "ntrs":
            urls.extend(await ntrs.get_urls(session, identifier))
        if mp == "osti":
            urls.extend(await osti.get_urls(session, identifier))
        if mp == "hal":
            urls.extend(await hal.get_urls(session, identifier))
        if mp == "scihub":
            urls.extend(await scihub.get_direct_urls(session, identifier))
        if mp == "scidb":
            urls.append(await scidb.get_url(session, identifier))
        if mp == "arxiv":
            urls.append(await arxiv.get_url(identifier))

    # if the catch-all "scihub" provider isn't given, we look for
    # specific Sci-Hub urls. if we find specific Sci-Hub URLs in the
    # user input, we only use those
    specific_providers = [p for p in providers if p not in matching_providers]
    if "scihub" not in providers and specific_providers:
        matching_scihub_urls = match_available_providers(
            specific_providers, await scihub.get_available_scihub_urls()
        )
        logger.info(f"matching scihub urls: {matching_scihub_urls}")
        if len(matching_scihub_urls) > 0:
            urls.extend(
                await scihub.get_direct_urls(
                    session, identifier, base_urls=matching_scihub_urls
                )
            )

    return urls


async def fetch(session, identifier, providers) -> tuple | None:
    # catch exceptions so that they don't cancel the task group
    async def get_wrapper(url):
        try:
            headers = None
            if urlsplit(url).hostname in {
                "pmc.ncbi.nlm.nih.gov",
                "www.biorxiv.org",
                "www.medrxiv.org",
            }:
                # These public download servers reject the generic aiohttp UA.
                # Keep other providers' existing defaults and honor -A overrides.
                headers = {
                    "User-Agent": session.headers.get("User-Agent", pmc.USER_AGENT)
                }
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30), headers=headers
            ) as response:
                response.raise_for_status()
                content = await response.read()
                source = str(response.url)
                if not content.startswith(b"%PDF-"):
                    completed = await pmc.complete_pdf_download(
                        session, response.url, content, headers
                    )
                    if completed:
                        content, source = completed
                # Repositories may serve PDFs as application/octet-stream;
                # conversely a PDF content type alone does not prove a PDF.
                if content.startswith(b"%PDF-"):
                    return content, source
                logger.info(
                    "No PDF returned (host={}, HTTP {}, type={!r}, bytes={})",
                    urlsplit(source).hostname,
                    response.status,
                    response.headers.get("Content-Type", "")[:120],
                    len(content),
                )
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error("error: {}", e)
        return None

    selected = (
        all_providers
        if providers == "all"
        else [p.strip() for p in providers.split(",")]
    )
    # Download before discovering the next provider, so a dead mirror or slow
    # repository cannot delay a PDF already found by an earlier provider.
    seen = set()
    for provider in selected:
        urls = await get_urls(session, identifier, provider)
        urls = list(dict.fromkeys(url for url in urls if url and url not in seen))
        seen.update(urls)
        tasks = [asyncio.create_task(get_wrapper(url)) for url in urls]
        try:
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    return result
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    return None


def save(data, path):
    """
    Save a file give data and a path.
    """
    try:
        logger.info(f"Saving file to {path}")

        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        logger.error(f"Failed to write to {path} {e}")
        raise e


def generate_name(content):
    "Generate unique filename for paper"

    pdf_hash = hashlib.md5(content).hexdigest()
    return f"{pdf_hash}" + ".pdf"


def rename(out_dir, path, name=None, identifier=None) -> str:
    """
    Renames a PDF to either the given name or its appropriate title, if
    possible. Adds the PDF extension. Returns the new path if renaming was
    successful, or the original path if not.
    """

    logger.info("Finding paper title")
    pdf2doi.config.set("verbose", False)

    try:
        if name is None:
            identifiers = parse_ids_from_text(identifier or "", ["doi"])
            raw_validation_info = None
            if len(identifiers) == 1:
                # The fetch already resolved this paper. Do not rediscover its
                # identifier by extracting the PDF and searching Google again.
                known = identifiers[0]
                raw_validation_info = pdf2doi.finders.validate(known["id"], known["type"])
            if not raw_validation_info:
                result_info = pdf2doi.pdf2doi(path)
                if not result_info:
                    return path
                raw_validation_info = result_info["validation_info"]
            if not raw_validation_info:
                return path
            if isinstance(raw_validation_info, (str, bytes, bytearray)):
                validation_info = json.loads(raw_validation_info)
            else:
                validation_info = raw_validation_info
            name = validation_info.get("title")

        if name:
            name = BeautifulSoup(name, "html.parser").get_text()
            name = name.replace("/", "_").replace("\\", "_")
            encoded_name = name.encode("utf-8")
            suffix = ".pdf"
            if len(encoded_name) + len(suffix) > 255:
                # Object stores may accept names that a local VFS cache cannot.
                # Keep complete UTF-8 characters and distinguish shared prefixes.
                suffix = f"-{hashlib.sha256(encoded_name).hexdigest()[:12]}.pdf"
                name = encoded_name[:255 - len(suffix)].decode("utf-8", errors="ignore")
            name += suffix
            new_path = os.path.join(out_dir, name)
            os.rename(path, new_path)
            logger.info(f"File renamed to {new_path}")
            return new_path
        else:
            return path
    except Exception as e:
        logger.error(f"Couldn't get paper title from PDF at {path}: {e}")
        return path
