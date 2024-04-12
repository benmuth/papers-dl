import argparse
import os
import re

import requests
from w3lib.encoding import html_body_declared_encoding, http_content_type_encoding

from scihub import IdentifierNotFoundError, SciHub
import pdf2doi
import json

# DOIs taken from https://www.crossref.org/blog/dois-and-matching-regular-expressions/
# listed in decreasing order of goodness. Not tested yet.
DOI_REGEXES = (
    re.compile(r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+", re.IGNORECASE),
    re.compile(r"10.1002\/[^\s]+", re.IGNORECASE),
    re.compile(
        r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d", re.IGNORECASE
    ),
    re.compile(r"10.1021\/\w\w\d++", re.IGNORECASE),
    re.compile(r"10.1207/[\w\d]+\&\d+_\d+", re.IGNORECASE),
)


# yoinked from archivebox/util.py
def download_url(url: str, timeout: int = 10) -> str:
    """Download the contents of a remote url and return the text"""
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
        },
        verify=True,
        timeout=timeout,
    )

    content_type = response.headers.get("Content-Type", "")
    encoding = http_content_type_encoding(content_type) or html_body_declared_encoding(
        response.text
    )

    if encoding is not None:
        response.encoding = encoding

    print(response.text)
    return response.text


def parse_dois_from_text(s: str) -> list[str]:
    for doi_regex in DOI_REGEXES:
        matches = doi_regex.findall(s)
        if matches:
            return matches
    return []


def filter_dois(doi_matches):
    # NOTE: Only keeping pdfs and matches without extensions.
    # Haven't tested if this is a reasonable filter
    filtered_dois = []
    for doi_match in doi_matches:
        if "." in os.path.basename(doi_match):
            _, ext = os.path.splitext(doi_match)
            if ext.lower() == ".pdf":
                filtered_dois.append(doi_match)
        else:
            filtered_dois.append(doi_match)
    return filtered_dois


def parse_dois_from_html(html):
    dois = set(parse_dois_from_text(html))
    print(f"unfiltered dois: {dois}")
    return filter_dois(dois)


def download_from_identifier(
    identifier: str, out: str, sh: SciHub, name: str | None = None
):
    result = sh.download(identifier, out)
    if not result:
        return

    if "err" in result:  # this is the API that scihub.py uses for errors
        print(f"{result['err']}")
        return
    else:
        print(f"Successfully downloaded file with identifier {identifier}")

    result_path = os.path.join(out, result["name"])

    try:
        result_info = pdf2doi.pdf2doi(result_path)
        validation_info = json.loads(result_info["validation_info"])
    except TypeError:
        print("Invalid JSON!")
        return

    title = validation_info.get("title")

    file_name = title if title else name
    if file_name:
        file_name += ".pdf"
        new_path = os.path.join(out, file_name)
        os.rename(result_path, new_path)
        print(f"File downloaded to {new_path}")


def save_scihub(identifier: str, out: str):
    sh = SciHub()
    # pdf2doi.pdf2doi.config.set()
    base_url_list = list(sh.available_base_url_list)
    if "http" in identifier:
        print(f"Attempting to download from {identifier}")
        try:
            download_from_identifier(identifier, out, sh)
        except IdentifierNotFoundError:
            print(
                "Identifier not found on sci-hub mirrors. Parsing HTML for new identifiers."
            )
            dois = parse_dois_from_html(download_url(identifier))
            if dois:
                print(f"Found DOIs in HTML: {dois}\n Attempting to download")
            else:
                print("No valid identifiers found")
            for doi in dois:
                sh.available_base_url_list = base_url_list
                download_from_identifier(doi, out, sh)
    elif ".pdf" in identifier:
        # pdf2doi can also take directories of pdfs, which will return a list of
        # dicts, but we're not handling that case here yet
        # TODO: look at error cases
        result = pdf2doi.pdf2doi(identifier)
        print(result["identifier"])

        validation_info = json.loads(result["validation_info"])
        references = validation_info["reference"]
        dois = [reference["DOI"] for reference in references if "DOI" in reference]
        # print(f'dois: {dois}')
        for doi in dois:
            download_from_identifier(doi, out, sh)
        # print('URL: %s' % validation_info['URL'])
    else:
        dois = parse_dois_from_text(identifier)
        print(f"Attempting to download from {dois}")
        if not dois:
            raise Exception("No DOIs found in input.")
        for doi in dois:
            download_from_identifier(doi, out, sh)


def main():
    # Some cli arguments from scihub.py
    parser = argparse.ArgumentParser(
        description="SciHub - To remove all barriers in the way of science."
    )
    parser.add_argument(
        "-d",
        "--download",
        metavar="(DOI|PMID|URL)",
        help="tries to find and download the paper with the given identifier",
        type=str,
    )
    parser.add_argument(
        "-f",
        "--file",
        metavar="path",
        help="pass file with list of newline separated identifiers and download each",
        type=str,
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="path",
        help="optional output directory for downloaded papers",
        default="",
        type=str,
    )
    args = parser.parse_args()

    if args.download:
        save_scihub(args.download, args.output)
    elif args.file:
        with open(args.file, "r") as f:
            identifiers = f.read().splitlines()
            for identifier in identifiers:
                save_scihub(identifier, args.output)


if __name__ == "__main__":
    main()
