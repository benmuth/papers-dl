from urllib.parse import urljoin

import logging

from parse.parse import find_pdf_url, parse_ids_from_text


async def get_url(session, identifier):
    base_url = "https://annas-archive.gs/scidb/"

    is_doi = parse_ids_from_text(identifier, ["doi"])
    if is_doi:
        url = urljoin(base_url, identifier)
        logging.info("searching SciDB: %s" % url)
        res = await session.get(url)
        pdf_url = find_pdf_url(await res.read())
        if pdf_url is None:
            logging.info("No direct link to PDF found from SciDB")
        return pdf_url

    return None


doi_regexes = [
    r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+",
    r"10.1002\/[^\s]+",
    r"10.\d{4}\/\d+-\d+X?(\d+)\d+<[\d\w]+:[\d\w]*>\d+.\d+.\w+;\d",
    r"10.1021\/\w\w\d++",
    r"10.1207/[\w\d]+\&\d+_\d+",
]
