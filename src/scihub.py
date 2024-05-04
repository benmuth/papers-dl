from collections.abc import MutableMapping
import re
import hashlib
import logging
import os

import requests
import urllib3
from bs4 import BeautifulSoup
from retrying import retry

import enum

# log config
logging.basicConfig()
logger = logging.getLogger("Sci-Hub")
logger.setLevel(logging.DEBUG)

urllib3.disable_warnings()

# URL-DIRECT - openly accessible paper
# URL-NON-DIRECT - pay-walled paper
# PMID - PubMed ID
# DOI - digital object identifier
IDClass = enum.Enum("identifier", ["URL-DIRECT", "URL-NON-DIRECT", "PMD", "DOI"])


class IdentifierNotFoundError(Exception):
    pass


class SiteAccessError(Exception):
    pass


class CaptchaNeededError(SiteAccessError):
    pass


class SciHub(object):
    """
    SciHub class can search for papers on Google Scholar
    and fetch/download papers from sci-hub.io
    """

    def __init__(self, user_agent):
        self.sess = requests.Session()
        self.sess.headers = {
            "User-Agent": user_agent,
        }
        self.available_base_url_list = self._get_available_scihub_urls()

        self.base_url = self.available_base_url_list[0] + "/"

    def _get_available_scihub_urls(self):
        """
        Finds available scihub urls via https://sci-hub.now.sh/
        """

        # NOTE: This misses some valid URLs. Alternatively, we could parse
        # the HTML more finely by navigating the parsed DOM, instead of relying
        # on filtering. That might be more brittle in case the HTML changes.
        # Generally, we don't need to get all URLs.
        scihub_domain = re.compile(r"^http[s]*://sci.hub", flags=re.IGNORECASE)
        urls = []
        res = requests.get("https://sci-hub.now.sh/")
        s = self._get_soup(res.content)
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
        if not self.available_base_url_list:
            logger.error("Ran out of valid sci-hub urls")
            raise IdentifierNotFoundError()
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + "/"
        logger.info("I'm changing to {}".format(self.available_base_url_list[0]))

    def download(self, identifier, destination="", path=None) -> dict[str, str] | None:
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        data = self.fetch(identifier)

        # TODO: allow for passing in name
        if data:
            self._save(
                data["pdf"],
                os.path.join(destination, path if path else data["name"]),
            )
        return data

    @retry(wait_random_min=100, wait_random_max=1000, stop_max_attempt_number=20)
    def fetch(self, identifier) -> dict[str, str | bytes | None] | None:
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """
        url = None
        try:
            # find the url to the pdf for a given identifier
            url = self._get_direct_url(identifier)
            logger.info("Found potential source at %s", identifier)

            # verify=False is dangerous but sci-hub.io
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            # NOTE(ben): see this SO answer: https://stackoverflow.com/questions/27068163/python-requests-not-handling-missing-intermediate-certificate-only-from-one-mach
            res = self.sess.get(url, verify=True)

            if res.headers["Content-Type"] != "application/pdf":
                logger.error(
                    "Failed to fetch PDF with identifier %s (resolved url %s) due to captcha, changing url...",
                    identifier,
                    url,
                )
                self._change_base_url()
                raise CaptchaNeededError("Failed to fetch PDF due to captcha")
            else:
                return {
                    "pdf": res.content,
                    "url": url,
                    "name": self._generate_name(res),
                }

        except Exception as e:
            logger.info(
                "Cannot access %s: %s, changing url...", self.available_base_url_list[0], e
            )
            self._change_base_url()
            raise SiteAccessError("Failed to access site")

    def _get_direct_url(self, identifier: str) -> str | None:
        """
        Finds the direct source url for a given identifier.
        """
        id_type = self._classify(identifier)

        if id_type == IDClass["URL-DIRECT"]:
            return identifier
        else:
            return self._search_direct_url(identifier)

    def _search_direct_url(self, identifier) -> str | None:
        """
        Sci-Hub embeds papers in an iframe. This function finds the actual
        source url which looks something like https://moscow.sci-hub.io/.../....pdf.
        """

        while True:
            res = self.sess.get(self.base_url + identifier, verify=True)
            s = self._get_soup(res.content)
            iframe = s.find("iframe")

            if iframe:
                src = iframe.get("src")
                if isinstance(src, list):
                    src = src[0]
                if src.startswith("//"):
                    return "http:" + src
                else:
                    return src

            else:
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

    def _save(self, data, path):
        """
        Save a file give data and a path.
        """
        try:
            with open(path, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.error("Failed to write to %s (%s)", path, e.__str__)
            raise e

    def _get_soup(self, html):
        """
        Return html soup.
        """
        return BeautifulSoup(html, "html.parser")

    def _generate_name(self, res):
        """
        Generate unique filename for paper. Returns a name by calcuating
        md5 hash of file contents, then appending the last 20 characters
        of the url which typically provides a good paper identifier.
        """
        name = res.url.split("/")[-1]
        name = re.sub("#view=(.+)", "", name)
        pdf_hash = hashlib.md5(res.content).hexdigest()
        return "%s-%s" % (pdf_hash, name[-20:])
