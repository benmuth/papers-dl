import argparse
import os
import re

import requests
from w3lib.encoding import html_body_declared_encoding, http_content_type_encoding

from scihub import IdentifierNotFoundError, SciHub
from parse import parse_file
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

recognized_identifiers = ["doi", "pmid", "url"]

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

    print(f"Successfully downloaded file with identifier {identifier}")

    # try to use actual title of paper
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
    dois = parse_dois_from_text(identifier)
    print(f"Attempting to download from {dois}")
    if not dois:
        raise Exception("No DOIs found in input.")
    for doi in dois:
        download_from_identifier(doi, out, sh)


def main():
    parser = argparse.ArgumentParser(
        description="Download scientific papers from the command line"
    )

    subparsers = parser.add_subparsers()

    # FETCH
    parser_fetch = subparsers.add_parser("fetch", help="try to download a paper from the given query")

    parser_fetch.add_argument(
        "query",
        metavar="(DOI|PMID|URL)",
        type=str,
        help="the identifier to try to download"
    )

    parser_fetch.add_argument(
        "-o",
        "--output",
        metavar="path",
        help="optional output directory for downloaded papers",
        default=".",
        type=str,
    )

    # PARSE
    parser_parse = subparsers.add_parser("parse", help="parse identifiers from a file")
    parser_parse.add_argument(
        "-m",
        "--match",
        metavar="type",
        help="the type of identifier to match",
        default="doi",
        type=str,
        choices=recognized_identifiers,
    )
    parser_parse.add_argument(
        "path",
        help="the path of the file to parse",
        type=str,
    )

    parser_fetch.set_defaults(func= lambda args: save_scihub(args.query, args.output))
    parser_parse.set_defaults(func= lambda args: parse_file(args.path,args.match))

    args = parser.parse_args()

    if hasattr(args, 'func'):
        print(args.func(args))


if __name__ == "__main__":
    main()
