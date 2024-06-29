from urllib.parse import urljoin

from parse.parse import find_pdf_url, parse_ids_from_text


async def get_url(session, identifier):
    base_url = "https://annas-archive.org/scidb/"

    is_doi = parse_ids_from_text(identifier, ["doi"])
    if is_doi:
        url = urljoin(base_url, identifier)
        res = await session.get(url)
        return find_pdf_url(await res.read())

    return None


doi_regexes = [
    r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
    r"10.1002\/[^\s]+",
    r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d",
    r"10.1021\/\w\w\d++",
    r"10.1207/[\w\d]+\&\d+_\d+",
]
