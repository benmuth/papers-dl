import argparse
import os

import requests
from w3lib.encoding import html_body_declared_encoding, http_content_type_encoding

from scihub import SciHub
from parse import parse_file
import pdf2doi
import json

supported_identifier_types = ["doi", "pmid", "url"]


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
    print(f"Attempting to download from {identifier}")
    download_from_identifier(identifier, out, sh)


def main():
    parser = argparse.ArgumentParser(
        description="Download scientific papers from the command line"
    )

    subparsers = parser.add_subparsers()

    # FETCH
    parser_fetch = subparsers.add_parser(
        "fetch", help="try to download a paper from the given query"
    )

    parser_fetch.add_argument(
        "query",
        metavar="(DOI|PMID|URL)",
        type=str,
        help="the identifier to try to download",
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
        choices=supported_identifier_types,
    )
    parser_parse.add_argument(
        "path",
        help="the path of the file to parse",
        type=str,
    )

    parser_fetch.set_defaults(func=lambda args: save_scihub(args.query, args.output))
    parser_parse.set_defaults(func=lambda args: parse_file(args.path, args.match))

    args = parser.parse_args()

    if hasattr(args, "func"):
        print(args.func(args))


if __name__ == "__main__":
    main()
