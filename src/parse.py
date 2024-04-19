import re
import os


# regexes taken from https://www.crossref.org/blog/dois-and-matching-regular-expressions/
# listed in decreasing order of goodness. Not tested yet.
patterns = {
    "url": [r'https?://[^\s<>"]+|www\.[^\s<>"]+'],
    "pmid": [r"PMID:?\s*(\d+)"],
    "doi": [
        r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
        r"10.1002\/[^\s]+",
        r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d",
        r"10.1021\/\w\w\d++",
        r"10.1207/[\w\d]+\&\d+_\d+",
    ],
}


def parse_ids_from_text(s: str, id_type: str) -> set[str]:
    matches = []
    for regex in patterns[id_type]:
        matches.extend(re.findall(regex, s, re.IGNORECASE))
    return set(matches)


def filter_dois(doi_matches: set[str]):
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
    try:
        print(path)
        with open(path) as f:
            content = f.read()
            return parse_ids_from_text(content, id_type)
    except Exception as e:
        print(f"Error: {e}")
