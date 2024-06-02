import argparse
import os
import sys
import logging


from scihub import SciHub
from parse import parse_file, format_output, parse_ids_from_text, id_patterns
import pdf2doi
import json

supported_fetch_identifier_types = ["doi", "pmid", "url", "isbn"]

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def save_scihub(
    identifier: str, out: str, user_agent: str, name: str | None = None
) -> str:
    """
    find a paper with the given identifier and download it to the output
    directory. If given, name will be the name of the output file. otherwise
    we attempt to find a title from the PDF contents.
    """

    sh = SciHub(user_agent)
    logging.info(f"Attempting to download paper with identifier {identifier}")

    result = sh.download(identifier, out)
    if not result:
        return ""

    logging.info(f"Successfully downloaded paper with identifier {identifier}")

    logging.info("Finding paper title")
    pdf2doi.config.set("verbose", False)
    result_path = os.path.join(out, result["name"])

    try:
        result_info = pdf2doi.pdf2doi(result_path)
        validation_info = json.loads(result_info["validation_info"])

        title = validation_info.get("title")

        file_name = name if name else title
        if file_name:
            file_name += ".pdf"
            new_path = os.path.join(out, file_name)
            os.rename(result_path, new_path)
            logging.info(f"File renamed to {new_path}")
            return new_path
    except Exception as e:
        logging.error(f"Couldn't get paper title from PDF at {result_path}: {e}")

    return result_path


def parse(args) -> str:
    # if a path isn't passed or is empty, read from stdin
    if not (hasattr(args, "path") and args.path):
        return format_output(parse_ids_from_text(sys.stdin.read(), args.match))

    return format_output(parse_file(args.path, args.match), args.format)


def fetch(args) -> str:
    path = save_scihub(args.query, args.output, args.user_agent)
    if path:
        return path
    else:
        return "No paper found"


def main():
    name = "papers-dl"
    parser = argparse.ArgumentParser(
        prog=name,
        description="Download scientific papers from the command line",
    )

    from version import __version__

    parser.add_argument(
        "--version", "-v", action="version", version=f"{name} {__version__}"
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
        default=None,
        type=str,
    )

    # PARSE
    parser_parse = subparsers.add_parser(
        "parse", help="parse identifiers from a file or stdin"
    )
    parser_parse.add_argument(
        "-m",
        "--match",
        metavar="type",
        help="the type of identifier to search for",
        type=str,
        choices=id_patterns.keys(),
        action="append",
    )
    parser_parse.add_argument(
        "-p",
        "--path",
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

    parser_fetch.set_defaults(func=fetch)
    parser_parse.set_defaults(func=parse)

    args = parser.parse_args()
    print(args.func(args))


if __name__ == "__main__":
    main()
