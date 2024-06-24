import re

import fetch_utils
import requests
from bs4 import BeautifulSoup
from pdf2doi import pdf2doi
import os

URL = "https://annas-archive.org/scidb/"


def find_pdf_url(html_content):
    s = BeautifulSoup(html_content, "html.parser")

    # look for a dynamically loaded PDF (scidb)
    script_element = s.find("script", string=re.compile("PDFObject.embed"))

    if script_element:
        match = re.search(r'PDFObject\.embed\("([^"]+)"', script_element.string)
        if match:
            return match.group(1)

    # look for the "<embed>" element (scihub)
    embed_element = s.find("embed", {"id": "pdf", "type": "application/pdf"})

    direct_url = None
    if embed_element:
        direct_url = embed_element["src"]
    if direct_url:
        return direct_url

    # look for an iframe
    iframe = s.find("iframe", {"type": "application/pdf"})

    src = None
    if iframe:
        src = iframe.get("src")
        if isinstance(src, list):
            src = src[0]
        if src.startswith("//"):
            direct_url = "http:" + src
        else:
            direct_url = src
    if direct_url:
        return direct_url

    return None


def fetch(identifier, session: requests.Session):
    full_url = URL + identifier
    res = session.get(url=full_url, verify=True)
    pdf_url = find_pdf_url(res.content)
    print(f"full url: {full_url}")
    if pdf_url:
        result = session.get(pdf_url, verify=True)
        return result.content
    else:
        return None


doi_regexes = [
    r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
    r"10.1002\/[^\s]+",
    r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d",
    r"10.1021\/\w\w\d++",
    r"10.1207/[\w\d]+\&\d+_\d+",
]


# TODO: deduplicate with parse.parse_ids_from_text
# this is only here because of errors importing
def parse_doi_from_text(s: str) -> list[dict[str, str]]:
    seen = set()
    matches = []
    for regex in doi_regexes:
        for match in re.findall(regex, s, re.IGNORECASE):
            if match not in seen:
                matches.append({"id": match, "type": "doi"})
            seen.add(match)
    return matches


def save_scidb(identifier, out, user_agent=None, name=None):
    sess = requests.Session()
    if user_agent is not None:
        sess.headers = {
            "User-Agent": user_agent,
        }

    # scidb only accepts DOI
    is_doi = parse_doi_from_text(identifier)
    # TODO: add exception handling
    if is_doi:
        result = fetch(identifier, sess)
        path = os.path.join(out, fetch_utils.generate_name(result))
        if result:
            with open(path, "wb") as f:
                f.write(result)
            new_path = fetch_utils.rename(out, path, name)
            return new_path
    raise Exception(f"identifer {identifier} source not found")
