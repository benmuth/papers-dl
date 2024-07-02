import argparse
import asyncio
import logging
import os
import sys

import aiohttp
from fetch import fetch_utils
from parse.parse import format_output, id_patterns, parse_file, parse_ids_from_text

supported_fetch_identifier_types = ["doi", "pmid", "url", "isbn"]


def parse_ids(args) -> str:
    output = None
    if hasattr(args, "path") and args.path:
        output = parse_file(args.path, args.match)
    else:
        # if a path isn't passed or is empty, read from stdin
        output = parse_ids_from_text(sys.stdin.read(), args.match)
    return format_output(output, args.format)


async def fetch(args):
    providers = args.providers
    id = args.query
    out = args.output

    headers = None
    if args.user_agent is not None:
        headers = {
            "User-Agent": args.user_agent,
        }

    async with aiohttp.ClientSession(headers=headers) as sess:
        pdf_content = await fetch_utils.fetch(
            sess,
            id,
            providers,
        )

    if pdf_content is None:
        return None
    path = os.path.join(out, fetch_utils.generate_name(pdf_content))
    fetch_utils.save(pdf_content, path)
    new_path = fetch_utils.rename(out, path)
    return new_path


async def main():
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
        default="all",
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
        if asyncio.iscoroutinefunction(args.func):
            result = await args.func(args)
        else:
            result = args.func(args)

        if result:
            print(result)
        else:
            print("No papers found")
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
