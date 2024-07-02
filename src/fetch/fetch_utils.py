import asyncio
import hashlib
import json
import logging
import os
from typing import Iterable

import aiohttp
import pdf2doi
import providers.scidb as scidb
import providers.scihub as scihub

all_providers = [
    "scihub",
    "scidb",
]


def match_available_providers(
    providers, available_providers: Iterable[str] | None = None
) -> list[str]:
    "Find the providers that are included in available_providers"
    if not available_providers:
        available_providers = all_providers
    matching_providers = []
    for provider in providers:
        for available_provider in available_providers:
            # a user-supplied provider might be a substring of a supported
            # provider (e.g. sci-hub.ee instead of https://sci-hub.ee)
            if provider in available_provider:
                matching_providers.append(available_provider)
    return matching_providers


async def get_urls(session, identifier, providers):
    urls = []
    if providers == "all":
        urls.append(await scidb.get_url(session, identifier))
        urls.extend(await scihub.get_direct_urls(session, identifier))
        return urls

    providers = [provider.strip() for provider in providers.split(",")]
    logging.info(f"given providers: {providers}")

    matching_providers = match_available_providers(providers)
    logging.info(f"matching providers: {matching_providers}")
    for mp in matching_providers:
        if mp == "scihub":
            urls.extend(await scihub.get_direct_urls(session, identifier))
        if mp == "scidb":
            urls.append(await scidb.get_url(session, identifier))

    # if the catch-all "scihub" provider isn't given, we look for
    # specific Sci-Hub urls. if we find specific Sci-Hub URLs in the
    # user input, only search those
    if "scihub" not in providers:
        matching_scihub_urls = match_available_providers(
            providers, await scihub.get_available_scihub_urls()
        )
        logging.info(f"matching scihub urls: {matching_scihub_urls}")
        if len(matching_scihub_urls) > 0:
            urls.extend(
                await scihub.get_direct_urls(
                    session, identifier, base_urls=matching_scihub_urls
                )
            )

    return urls


async def fetch(session, identifier, providers):
    async def get_wrapper(url):
        try:
            return await session.get(url)
        except Exception as e:
            logging.error("error: %s" % e)
            return None

    urls = await get_urls(session, identifier, providers)

    logging.info("PDF urls: %s" % "\n".join(urls))
    tasks = [get_wrapper(url) for url in urls if url]
    for item in zip(asyncio.as_completed(tasks), urls):
        res = await item[0]
        if res is None or res.content_type != "application/pdf":
            logging.info("couldn't find url at %s" % item[1])
            continue
        return await res.read()
    return None


def save(data, path):
    """
    Save a file give data and a path.
    """
    try:
        logging.info(f"Saving file to {path}")

        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        logging.error(f"Failed to write to {path} {e}")
        raise e


def generate_name(content):
    "Generate unique filename for paper"

    pdf_hash = hashlib.md5(content).hexdigest()
    return f"{pdf_hash}" + ".pdf"


def rename(out_dir, path, name=None) -> str:
    """
    Renames a PDF to either the given name or its appropriate title, if
    possible. Adds the PDF extension. Returns the new path if renaming was
    successful, or the original path if not.
    """

    logging.info("Finding paper title")
    pdf2doi.config.set("verbose", False)

    try:
        if name is None:
            result_info = pdf2doi.pdf2doi(path)
            validation_info = json.loads(result_info["validation_info"])
            name = validation_info.get("title")

        if name:
            name += ".pdf"
            new_path = os.path.join(out_dir, name)
            os.rename(path, new_path)
            logging.info(f"File renamed to {new_path}")
            return new_path
        else:
            return path
    except Exception as e:
        logging.error(f"Couldn't get paper title from PDF at {path}: {e}")
        return path
