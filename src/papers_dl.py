import argparse
import os
import sys
import logging


from scihub import SciHub
from parse import parse_file, format_output, parse_ids_from_text, id_patterns

import pdf2doi
import json

supported_fetch_identifier_types = ["doi", "pmid", "url", "isbn"]

supported_providers = ["sci-hub"]


def save_scihub(
    identifier: str,
    out: str,
    base_urls: list[str] | None = None,
    user_agent: str | None = None,
    name: str | None = None,
) -> str:
    """
    Find a paper with the given identifier and download it to the output
    directory.

    If given, name will be the name of the output file. Otherwise we attempt to
    find a title from the PDF contents. If no name is found, one is generated
    from a hash of the contents.

    base_urls is an optional list of SciHub urls to search. If not given, it
    will default to searching all SciHub mirrors it can find.
    """

    sh = SciHub(base_urls, user_agent)
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


def parse_ids(args) -> str:
    # if a path isn't passed or is empty, read from stdin
    if not (hasattr(args, "path") and args.path):
        return format_output(parse_ids_from_text(sys.stdin.read(), args.match))

    return format_output(parse_file(args.path, args.match), args.format)


provider_functions = {
    "sci-hub": save_scihub,
}


def match_available_providers(providers, available_providers) -> list[str]:
    matching_providers = []
    for p in providers:
        matching_providers.extend([s for s in available_providers if p in s])
    return matching_providers


def fetch(args) -> list[str]:
    providers = args.providers
    paths = []

    if providers == "auto":
        # TODO: add more providers and return early on success
        paths.append(save_scihub(args.query, args.output, user_agent=args.user_agent))
    else:
        supported_providers = list(provider_functions.keys())
        providers = [x.strip() for x in providers.split(",")]

        matching_providers = match_available_providers(providers, supported_providers)
        for mp in matching_providers:
            paths.append(
                provider_functions[mp](
                    args.query,
                    args.output,
                    user_agent=args.user_agent,
                )
            )

        matching_scihub_urls = []
        # if scihub is given, we don't need to find matching urls
        if "scihub" not in providers:
            sh = SciHub()
            available_scihub_providers = sh.available_base_url_list
            matching_scihub_urls = match_available_providers(
                providers, available_scihub_providers
            )

        # if we have specific URLs, just search those
        results = []
        if len(matching_scihub_urls) > 0:
            results = save_scihub(
                args.query,
                args.output,
                base_urls=matching_scihub_urls,
                user_agent=args.user_agent,
            )
        else:
            results = save_scihub(
                args.query,
                args.output,
                user_agent=args.user_agent,
            )

        paths.extend([r for r in results if len(r) > 0])
        return paths

    return paths


def main():
    name = "papers-dl"
    parser = argparse.ArgumentParser(
        prog=name,
        description="Download scientific papers from the command line",
    )

    from version import __version__

    parser.add_argument(
        "--version", "-V", action="version", version=f"{name} {__version__}"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="increase verbosity"
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
        "-p",
        "--providers",
        help="comma separated list of providers to try fetching from",
        default="auto",
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
    parser_parse.set_defaults(func=parse_ids)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    if hasattr(args, "func"):
        print(args.func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
