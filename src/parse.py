import re
import json


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


def parse_ids_from_text(s: str, id_type: str) -> list[tuple[str, str]]:
    matches = []
    for regex in id_patterns[id_type]:
        for match in re.findall(regex, s, re.IGNORECASE):
            matches.append((id_type, match))
    return matches


def parse_file(path, id_types: list[str]):
    """
    Find all matches for the given id type in a file.
    """
    print(f"Parsing {path}")
    print(f"id_type: {id_types}")

    matches = []
    try:
        with open(path) as f:
            content = f.read()
        for id_type in id_types:
            matches.extend(parse_ids_from_text(content, id_type))
    except Exception as e:
        print(f"Error: {e}")

    return matches


def print_output(output: list[tuple[str, str]], format: str) -> None:
    if format == "raw":
        for line in output:
            print(line[1])
    elif format == "jsonl":
        for line in output:
            print(json.dumps({"id": line[1], "type": line[0]}))
    elif format == "csv":
        for line in output:
            print(line[0], end=",")
            print(line[1])
    else:
        print(output)
