import argparse
import os

import requests
from w3lib.encoding import html_body_declared_encoding, http_content_type_encoding

from scihub import SciHub
from parse import parse_file, print_output, id_patterns
import pdf2doi
import json

supported_fetch_identifier_types = ["doi", "pmid", "url", "isbn"]


DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"


def save_scihub(identifier: str, out: str, user_agent: str, name: str | None = None):
    """
    find a paper with the given identifier and download it to the output 
    directory. If given, name will be the name of the output file. otherwise
    we attempt to find a title from the PDF contents.
    """

    sh = SciHub(user_agent)
    print(f"Attempting to download from {identifier}")

    result = sh.download(identifier, out)
    if not result:
        return

    print(f"Successfully downloaded file with identifier {identifier}")

    # try to use actual title of paper
    pdf2doi.config.set("verbose", False)
    result_path = os.path.join(out, result["name"])

    try:
        result_info = pdf2doi.pdf2doi(result_path)
        validation_info = json.loads(result_info["validation_info"])
    except TypeError:
        print("Invalid JSON!")
        return

    title = validation_info.get("title")

    file_name = name if name else title
    if file_name:
        file_name += ".pdf"
        new_path = os.path.join(out, file_name)
        os.rename(result_path, new_path)
        print(f"File downloaded to {new_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Download scientific papers from the command line"
    )

    subparsers = parser.add_subparsers()

    # FETCH
    parser_fetch = subparsers.add_parser(
        "fetch", help="try to download a paper with the given identifier"
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

    parser_fetch.add_argument(
        "-A",
        "--user-agent",
        help="",
        default=DEFAULT_USER_AGENT,
        type=str,
    )

    # PARSE
    parser_parse = subparsers.add_parser("parse", help="parse identifiers from a file")
    parser_parse.add_argument(
        "-m",
        "--match",
        metavar="type",
        help="the type of identifier to match",
        type=str,
        # choices=id_patterns.keys(),
        action="append",
        # nargs="+",
    )
    parser_parse.add_argument(
        "path",
        help="the path of the file to parse",
        type=str,
    )
    parser_parse.add_argument(
        "-f",
        "--format",
        help="the output format for printing",
        metavar="fmt",
        default="raw",
        choices=["raw", "jsonl", "csv"],
        nargs="?",
    )

    parser_fetch.set_defaults(
        func=lambda fetch_args: save_scihub(
            fetch_args.query, fetch_args.output, fetch_args.user_agent
        )
    )
    parser_parse.set_defaults(
        func=lambda parse_args: print_output(
            parse_file(parse_args.path, parse_args.match),
            parse_args.format,
        )
    )

    args = parser.parse_args()

    if hasattr(args, "func"):
        print(args.func(args))


if __name__ == "__main__":
    main()
