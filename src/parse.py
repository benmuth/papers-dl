import re


patterns = {
    "url": r'https?://[^\s<>"]+|www\.[^\s<>"]+',
    "pmid": r'PMID:?\s*(\d+)',
    "doi": r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
}

def parse_ids(content, id_type):
    try:
        ids = re.findall(patterns[id_type], content, re.IGNORECASE)
        return ids

    except Exception as e:
        print(f'An error occurred: {e}')

