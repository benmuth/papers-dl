import asyncio
import enum
import logging
import os
import re

import aiohttp
import urllib3
from bs4 import BeautifulSoup
from fetch import fetch_utils

# from retrying import retry
import random


async def save_scihub(
    session: aiohttp.ClientSession,
    identifier: str,
    out: str,
    base_urls: list[str] | None = None,
    name: str | None = None,
) -> str | None:
    """
    Find a paper with the given identifier and download it to the output
    directory.

    If given, name will be the name of the output file. Otherwise we attempt to
    find a title from the PDF contents. If no name is found, one is generated
    from a hash of the contents.

    base_urls is a list of Sci-Hub urls to search.
    """
    if not base_urls:
        base_urls = await SciHub.get_available_scihub_urls()

    sh = SciHub(session, base_urls=base_urls)
    logging.info(f"Attempting to download paper with identifier {identifier}")

    result = await sh.download(identifier, out)
    if not result:
        return None

    logging.info(f"Successfully downloaded paper with identifier {identifier}")

    path = fetch_utils.rename(out, os.path.join(out, result["name"]), name)

    return path


urllib3.disable_warnings()

# URL-DIRECT - openly accessible paper
# URL-NON-DIRECT - pay-walled paper
# PMID - PubMed ID
# DOI - digital object identifier
IDClass = enum.Enum("identifier", ["URL-DIRECT", "URL-NON-DIRECT", "PMD", "DOI"])

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"


class IdentifierNotFoundError(Exception):
    pass


class SiteAccessError(Exception):
    pass


class CaptchaNeededError(SiteAccessError):
    pass


class SciHub(object):
    """
    Sci-Hub class can search for papers on Google Scholar
    and fetch/download papers from sci-hub.io
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_urls: list[str],
    ):
        self.sess = session
        self.available_base_url_list = base_urls
        self.base_url = self.available_base_url_list[0] + "/"

    @staticmethod
    async def get_available_scihub_urls() -> list[str]:
        """
        Finds available Sci-Hub urls via https://sci-hub.now.sh/
        """

        # NOTE: This misses some valid URLs. Alternatively, we could parse
        # the HTML more finely by navigating the parsed DOM, instead of relying
        # on filtering. That might be more brittle in case the HTML changes.
        # Generally, we don't need to get all URLs.
        scihub_domain = re.compile(r"^http[s]*://sci.hub", flags=re.IGNORECASE)
        urls = []
        # async with aiohttp.ClientSession() as session:
        async with aiohttp.request("GET", "https://sci-hub.now.sh/") as res:
            s = BeautifulSoup(await res.text(), "html.parser")
            text_matches = s.find_all(
                "a",
                href=True,
                string=re.compile(scihub_domain),
            )
            href_matches = s.find_all(
                "a",
                re.compile(scihub_domain),
                href=True,
            )
            full_match_set = set(text_matches) | set(href_matches)
            for a in full_match_set:
                if "sci" in a or "sci" in a["href"]:
                    urls.append(a["href"])
        return urls

    def _change_base_url(self):
        if len(self.available_base_url_list) <= 1:
            raise IdentifierNotFoundError("Ran out of valid Sci-Hub urls")
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + "/"

        logging.info("Changing URL to {}".format(self.available_base_url_list[0]))

    async def download(
        self, identifier, destination="", path=None
    ) -> dict[str, str] | None:
        """
        Downloads a paper from Sci-Hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        try:
            data = await self.fetch(identifier)

            # TODO: allow for passing in name
            if data:
                fetch_utils.save(
                    data["pdf"],
                    os.path.join(destination, path if path else data["name"]),
                )
            return data
        except IdentifierNotFoundError as infe:
            logging.error(f"Failed to find identifier {identifier}: {infe}")

    async def fetch(self, identifier) -> dict | None:
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """
        logging.info(f"Looking for {identifier}")
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                # find the url to the pdf for a given identifier
                url = await self._get_direct_url(identifier)
                logging.info(f"Found potential source at {url}")

                async with self.sess.get(url) as res:
                    if res.content_type != "application/pdf":
                        logging.error(
                            f"Couldn't find PDF with identifier {identifier} at URL {url}, changing base url..."
                        )
                        raise SiteAccessError("Couldn't find PDF")
                    else:
                        return {
                            "pdf": await res.read(),
                            "url": url,
                            "name": fetch_utils.generate_name(await res.read()),
                        }
            except (IdentifierNotFoundError, IndexError):
                raise
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise IdentifierNotFoundError
                logging.info(
                    f"Cannot access source from {self.available_base_url_list[0]}: {e}, changing base URL..."
                )
                self._change_base_url()
                await asyncio.sleep(random.uniform(0.1, 1.0))

    async def _get_direct_url(self, identifier: str) -> str:
        """
        Finds the direct source url for a given identifier.
        """
        id_type = self._classify(identifier)

        if id_type == IDClass["URL-DIRECT"]:
            return identifier

        # Sci-Hub embeds PDFs in an iframe or similar. This finds the actual
        # source url which looks something like https://sci-hub.ee/...pdf.
        while True:
            async with self.sess.get(self.base_url + identifier) as res:
                path = fetch_utils.find_pdf_url(await res.text())

            if isinstance(path, list):
                path = path[0]
            if isinstance(path, str) and path.startswith("//"):
                return "https:" + path
            if isinstance(path, str) and path.startswith("/"):
                return self.base_url + path
            self._change_base_url()

    def _classify(self, identifier) -> IDClass:
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
