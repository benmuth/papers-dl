import re
import json

# these are the currently supported identifier types that we can parse, along
# with their regex patterns
id_patterns = {
    # These come from https://gist.github.com/oscarmorrison/3744fa216dcfdb3d0bcb
    "isbn": [
        r"(?:ISBN(?:-10)?:?\ )?(?=[0-9X]{10}|(?=(?:[0-9]+[-\ ]){3})[-\ 0-9X]{13})[0-9]{1,5}[-\ ]?[0-9]+[-\ ]?[0-9]+[-\ ]?[0-9X]",
        r"(?:ISBN(?:-13)?:?\ )?(?=[0-9]{13}|(?=(?:[0-9]+[-\ ]){4})[-\ 0-9]{17})97[89][-\ ]?[0-9]{1,5}[-\ ]?[0-9]+[-\ ]?[0-9]+[-\ ]?[0-9]",
    ],
    # doi regexes taken from https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    # listed in decreasing order of goodness. Not fully tested yet.
    "doi": [
        r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
        r"10.1002\/[^\s]+",
        r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d",
        r"10.1021\/\w\w\d++",
        r"10.1207/[\w\d]+\&\d+_\d+",
    ],
}


def parse_ids_from_text(
    s: str, id_types: list[str] | None = None
) -> list[dict[str, str]]:
    """
    Find all matches for the given id types in s. If id_types isn't given,
    defaults to the types in id_patterns.
    """

    # we look for all ID patterns by default
    if id_types is None:
        id_types = list(id_patterns)

    seen = set()
    matches = []
    for id_type in id_types:
        for regex in id_patterns[id_type]:
            for match in re.findall(regex, s, re.IGNORECASE):
                if match not in seen:
                    matches.append({"id": match, "type": id_type})
                seen.add(match)
    return matches


def parse_file(path, id_types: list[str] | None = None):
    """
    Find all matches for the given id types in a file. If id_types isn't given,
    defaults to the types in id_patterns.
    """

    matches = []
    try:
        with open(path) as f:
            content = f.read()
        matches = parse_ids_from_text(content, id_types)
    except Exception as e:
        print(f"Error: {e}")

    return matches


def format_output(output: list[dict[str, str]], format: str = "raw") -> str:
    """
    Formats a list of dicts of ids and id types into a string according to the
    given format type. 'raw' formats ids by line, ignoring type. 'jsonl' and
    'csv' formats ids and types.
    """

    lines: list[str] = []
    if format == "raw":
        lines = [line["id"] for line in output]
    elif format == "jsonl":
        lines = [json.dumps(line) for line in output]
    elif format == "csv":
        lines = [f"{line['id']},{line['type']}" for line in output]
    return "\n".join(lines)
