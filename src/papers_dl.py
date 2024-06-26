import argparse
import logging
import sys
from typing import Iterable

from parse.parse import format_output, id_patterns, parse_file, parse_ids_from_text
from providers.scidb import save_scidb
from providers.scihub import SciHub, save_scihub

supported_fetch_identifier_types = ["doi", "pmid", "url", "isbn"]

provider_functions = {
    "scihub": save_scihub,
    "scidb": save_scidb,
}


def parse_ids(args) -> str:
    # if a path isn't passed or is empty, read from stdin
    if not (hasattr(args, "path") and args.path):
        return format_output(parse_ids_from_text(sys.stdin.read(), args.match))

    return format_output(parse_file(args.path, args.match), args.format)


def match_available_providers(
    providers, available_providers: Iterable[str] | None = None
) -> list[str]:
    "Find the providers that are included in available_providers"
    if not available_providers:
        available_providers = provider_functions.keys()
    matching_providers = []
    for provider in providers:
        for available_provider in available_providers:
            # a user-supplied provider might be a substring of a supported
            # provider (sci-hub.ee instead of https://sci-hub.ee)
            if provider in available_provider:
                matching_providers.append(available_provider)
    return matching_providers


def fetch(args) -> list[str]:
    providers = args.providers
    paths = []

    if providers == "auto":
        # TODO: add more providers and return early on success
        paths.append(save_scidb(args.query, args.output, user_agent=args.user_agent))
        paths.append(save_scihub(args.query, args.output, user_agent=args.user_agent))
    else:
        providers = [x.strip() for x in providers.split(",")]
        logging.info(f"given providers: {providers}")

        matching_providers = match_available_providers(providers)
        logging.info(f"matching providers: {matching_providers}")
        for mp in matching_providers:
            paths.append(
                provider_functions[mp](
                    args.query,
                    args.output,
                    user_agent=args.user_agent,
                )
            )

        result_path = None
        # if the catch-all "scihub" provider isn't given, we look for specific
        # Sci-Hub urls
        # if we find specific Sci-Hub URLs in the user input, only search those
        if "scihub" not in providers:
            available_scihub_providers = SciHub.get_available_scihub_urls()
            matching_scihub_urls = match_available_providers(
                providers, available_scihub_providers
            )
            logging.info(f"matching scihub urls: {matching_scihub_urls}")
            if len(matching_scihub_urls) > 0:
                result_path = save_scihub(
                    args.query,
                    args.output,
                    user_agent=args.user_agent,
                    base_urls=matching_scihub_urls,
                )

        if result_path:
            paths.append(result_path)
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
        result = args.func(args)
        if result:
            print(result)
        else:
            print("No papers found")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
