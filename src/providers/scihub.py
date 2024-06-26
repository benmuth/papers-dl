import enum
import hashlib
import json
import logging
import os
import re

import requests
import urllib3
from bs4 import BeautifulSoup
from fetch import fetch_utils
from pdf2doi import pdf2doi
from retrying import retry


def save_scihub(
    identifier: str,
    out: str,
    base_urls: list[str] | None = None,
    user_agent: str | None = None,
    name: str | None = None,
) -> str | None:
    """
    Find a paper with the given identifier and download it to the output
    directory.

    If given, name will be the name of the output file. Otherwise we attempt to
    find a title from the PDF contents. If no name is found, one is generated
    from a hash of the contents.

    base_urls is an optional list of Sci-Hub urls to search. If not given, it
    will default to searching all Sci-Hub mirrors it can find.
    """

    sh = SciHub(base_urls, user_agent)
    logging.info(f"Attempting to download paper with identifier {identifier}")

    result = sh.download(identifier, out)
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
        base_urls: list[str] | None = None,
        user_agent: str | None = DEFAULT_USER_AGENT,
    ):
        self.sess = requests.Session()
        if user_agent is not None:
            self.sess.headers = {
                "User-Agent": user_agent,
            }
        self.available_base_url_list = (
            base_urls if base_urls else SciHub.get_available_scihub_urls()
        )

        self.base_url = self.available_base_url_list[0] + "/"

    @staticmethod
    def get_available_scihub_urls() -> list[str]:
        """
        Finds available Sci-Hub urls via https://sci-hub.now.sh/
        """

        # NOTE: This misses some valid URLs. Alternatively, we could parse
        # the HTML more finely by navigating the parsed DOM, instead of relying
        # on filtering. That might be more brittle in case the HTML changes.
        # Generally, we don't need to get all URLs.
        scihub_domain = re.compile(r"^http[s]*://sci.hub", flags=re.IGNORECASE)
        urls = []
        res = requests.get("https://sci-hub.now.sh/")
        s = BeautifulSoup(res.content, "html.parser")
        text_matches = s.find_all("a", href=True, string=re.compile(scihub_domain))
        href_matches = s.find_all("a", re.compile(scihub_domain), href=True)
        full_match_set = set(text_matches) | set(href_matches)
        for a in full_match_set:
            if "sci" in a or "sci" in a["href"]:
                urls.append(a["href"])
        return urls

    def set_proxy(self, proxy):
        """
        set proxy for session
        :param proxy_dict:
        :return:
        """
        if proxy:
            self.sess.proxies = {
                "http": proxy,
                "https": proxy,
            }

    def _change_base_url(self):
        if len(self.available_base_url_list) <= 1:
            raise IdentifierNotFoundError("Ran out of valid Sci-Hub urls")
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + "/"

        logging.info("Changing URL to {}".format(self.available_base_url_list[0]))

    def download(self, identifier, destination="", path=None) -> dict[str, str] | None:
        """
        Downloads a paper from Sci-Hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        try:
            data = self.fetch(identifier)

            # TODO: allow for passing in name
            if data:
                fetch_utils.save(
                    data["pdf"],
                    os.path.join(destination, path if path else data["name"]),
                )
            return data
        except IdentifierNotFoundError as infe:
            logging.error(f"Failed to find identifier {identifier}: {infe}")

    @retry(
        wait_random_min=100,
        wait_random_max=1000,
        stop_max_attempt_number=20,
        retry_on_exception=lambda e: not (
            isinstance(e, IdentifierNotFoundError) or isinstance(e, IndexError)
        ),
    )
    def fetch(self, identifier) -> dict | None:
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """
        logging.info(f"Looking for {identifier}")
        try:
            # find the url to the pdf for a given identifier
            url = self._get_direct_url(identifier)
            logging.info(f"Found potential source at {url}")

            # verify=False is dangerous but Sci-Hub.io
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            # NOTE(ben): see this SO answer: https://stackoverflow.com/questions/27068163/python-requests-not-handling-missing-intermediate-certificate-only-from-one-mach
            # verify=True seems to be working okay
            res = self.sess.get(url, verify=True)

            if res.headers["Content-Type"] != "application/pdf":
                logging.error(
                    f"Couldn't find PDF with identifier {identifier} at URL {url}, changing base url..."
                )
                raise SiteAccessError("Couldn't find PDF")
            else:
                return {
                    "pdf": res.content,
                    "url": url,
                    "name": fetch_utils.generate_name(res.content),
                }

        except IdentifierNotFoundError:
            raise
        except Exception as e:
            logging.info(
                f"Cannot access source from {self.available_base_url_list[0]}: {e}, changing base URL..."
            )
            self._change_base_url()
            raise SiteAccessError from e

    def _get_direct_url(self, identifier: str) -> str:
        """
        Finds the direct source url for a given identifier.
        """
        id_type = self._classify(identifier)

        if id_type == IDClass["URL-DIRECT"]:
            return identifier

        # Sci-Hub embeds PDFs in an iframe or similar. This finds the actual
        # source url which looks something like https://sci-hub.ee/...pdf.
        while True:
            res = self.sess.get(self.base_url + identifier, verify=True)
            path = fetch_utils.find_pdf_url(res.content)

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
