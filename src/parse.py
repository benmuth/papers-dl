import re
import os
import json


id_patterns = {
    # These come from https://gist.github.com/oscarmorrison/3744fa216dcfdb3d0bcb
    "isbn": [
        r"(?:ISBN(?:-10)?:?\ )?(?=[0-9X]{10}|(?=(?:[0-9]+[-\ ]){3})[-\ 0-9X]{13})[0-9]{1,5}[-\ ]?[0-9]+[-\ ]?[0-9]+[-\ ]?[0-9X]",
        r"(?:ISBN(?:-13)?:?\ )?(?=[0-9]{13}|(?=(?:[0-9]+[-\ ]){4})[-\ 0-9]{17})97[89][-\ ]?[0-9]{1,5}[-\ ]?[0-9]+[-\ ]?[0-9]+[-\ ]?[0-9]",
    ],
    # doi regexes taken from https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    # listed in decreasing order of goodness. Not tested yet.
    "doi": [
        r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
        r"10.1002\/[^\s]+",
        r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d",
        r"10.1021\/\w\w\d++",
        r"10.1207/[\w\d]+\&\d+_\d+",
    ],
}

def parse_ids_from_text(s: str, id_types: list[str]) -> list[tuple[str, str]]:
    matches = []
    for id_type in id_types:
        for regex in id_patterns[id_type]:
            for match in re.findall(regex, s, re.IGNORECASE):
                matches.append((id_type, match))
    return matches


def filter_dois(doi_matches: list[str]):
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


def parse_file(path, id_type):
    print(f"Parsing {path}")
    try:
        with open(path) as f:
            content = f.read()
        return parse_ids_from_text(content, id_type)
    except Exception as e:
        print(f"Error: {e}")
        return []


def print_output(output: list[tuple[str, str]], format: str) -> None:
    if format == "raw":
        for line in output:
            print(line[1])
    elif format == "jsonl":
        for line in output:
            print(json.dumps({"id": line[1], "type": line[0]}))
    elif format == "csv":
        for line in output:
            for i in range(len(line)):
                if i < len(line) - 1:
                    print(line[i], end=",")
                else:
                    print(line[i])
    else:
        print(output)
