# -*- coding: utf-8 -*-

# I modified this in a few ways from the `scihub.py` GH repo:
# - the user agent is changed to work on my Mac
# - it will now search through all Sci-Hub links from sci-hub.now.sh for the source PDF
# instead of giving up after the first one
# - I added a specific exception for when no identifier matches in any base Sci-Hub url

"""
Sci-API Unofficial API
[Search|Download] research papers from [scholar.google.com|sci-hub.io].

@author zaytoun
"""

from collections.abc import MutableMapping
import re
import argparse
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

#
urllib3.disable_warnings()


# URL-DIRECT - openly accessible paper
# URL-NON-DIRECT - pay-walled paper
# PMID - PubMed ID
# DOI - digital object identifier
IDClass = enum.Enum("identifier", ["URL-DIRECT", "URL-NON-DIRECT", "PMD", "DOI"])

# constants
SCHOLARS_BASE_URL = "https://scholar.google.com/scholar"
HEADERS: MutableMapping = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
}


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

    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers = HEADERS
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
            logger.critical("Ran out of valid sci-hub urls")
            raise IdentifierNotFoundError()
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + "/"
        logger.info("I'm changing to {}".format(self.available_base_url_list[0]))

    def search(self, query, limit=10, download=False):
        """
        Performs a query on scholar.google.com, and returns a dictionary
        of results in the form {'papers': ...}. Unfortunately, as of now,
        captchas can potentially prevent searches after a certain limit.
        """
        start = 0
        results = {"papers": []}

        while True:
            try:
                res = self.sess.get(
                    SCHOLARS_BASE_URL, params={"q": query, "start": start}
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Failed to complete search with query %s (connection error)", query
                )
                raise e

            s = self._get_soup(res.content)
            papers = s.find_all("div", class_="gs_r")

            if not papers:
                if "CAPTCHA" in str(res.content):
                    logger.error(
                        "Failed to complete search with query %s (captcha)", query
                    )
                    raise SiteAccessError

            for paper in papers:
                if not paper.find("table"):
                    source = None
                    pdf = paper.find("div", class_="gs_ggs gs_fl")
                    link = paper.find("h3", class_="gs_rt")

                    if pdf:
                        source = pdf.find("a")["href"]
                    elif link.find("a"):
                        source = link.find("a")["href"]
                    else:
                        continue

                    results["papers"].append({"name": link.text, "url": source})

                    if len(results["papers"]) >= limit:
                        return results

            start += 10

    @retry(wait_random_min=100, wait_random_max=1000, stop_max_attempt_number=10)
    def download(self, identifier, destination="", path=None):
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        data = self.fetch(identifier)

        # TODO: allow for passing in name
        if data:
            self._save(
                data["pdf"], os.path.join(destination, path if path else data["name"])
            )
        return data

    def fetch(self, identifier) -> dict[str, bytes | str] | None:
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """
        url = None
        try:
            url = self._get_direct_url(identifier)
            if not url:
                raise ValueError("No URL found")
            # verify=False is dangerous but sci-hub.io
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            # NOTE(ben): see this SO answer: https://stackoverflow.com/questions/27068163/python-requests-not-handling-missing-intermediate-certificate-only-from-one-mach
            res = self.sess.get(url, verify=True)

            if res.headers["Content-Type"] != "application/pdf":
                logger.info(
                    "Failed to fetch pdf with identifier %s (resolved url %s) due to captcha",
                    identifier,
                    url,
                )
                self._change_base_url()
                raise SiteAccessError()
            else:
                return {
                    "pdf": res.content,
                    "url": url,
                    "name": self._generate_name(res),
                }

        except requests.exceptions.ConnectionError as e:
            logger.info(
                "Cannot access %s, changing url", self.available_base_url_list[0]
            )
            self._change_base_url()
            raise e

        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to fetch pdf with identifier %s (resolved url %s) due to request exception.",
                identifier,
                url,
            )
            return None

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
            logger.info("Failed to write to %s (%s)", path, e.__str__)
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
