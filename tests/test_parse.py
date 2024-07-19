import os
import unittest

from parse import parse

target_ids = ("doi", "pmid", "isbn", "issn", "url", "arxiv")


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_material_dir = "tests/documents"
        cls.valid_id_types = parse.id_patterns.keys()
        for id_type in target_ids:
            if id_type not in cls.valid_id_types:
                print(f"Skipping testing for {id_type} parsing")

    def test_parse_text_ids(self):
        "Test to parse identifiers from a set of files."

        # NOTE: this test does not fail on false positive matches
        # for file in test_document_ids:
        for file in test_document_ids:
            print(f"testing {file}")
            with open(os.path.join(TestParser.test_material_dir, file)) as f:
                file_content = f.read()

            parsed_results = parse.parse_ids_from_text(file_content)

            # just include the matching id, not the type
            parsed_results = [result["id"] for result in parsed_results]

            expected_ids = []
            for type in test_document_ids[file]:
                if type in parse.id_patterns:
                    for id in test_document_ids[file][type]:
                        expected_ids.append(id)

            if not expected_ids:
                print("No expected IDs for this file")
                continue

            for expected_id in expected_ids:
                self.assertIn(
                    expected_id,
                    parsed_results,
                    f"ID {expected_id} not found in {file}",
                )

    def test_parse_text_pdfs(self):
        for file, expected_url in test_document_links:
            with open(os.path.join(TestParser.test_material_dir, file), "rt") as f:
                html_content = f.read()
                pdf_url = parse.find_pdf_url(html_content)
            self.assertEqual(pdf_url, expected_url)


test_document_ids = {
    "ids.txt": {
        "url": [
            "https://www.cell.com/current-biology/fulltext/S0960-9822(19)31469-1",
        ],
        "doi": [
            "10.1016/j.cub.2019.11.030",
            "10.1107/s0907444905036693",
        ],
    },
    "bsp-tree.html": {
        "doi": [
            "10.1109/83.544569",
        ],
        "issn": [
            "1057-7149",
            "1941-0042",
        ],
    },
    "reyes-rendering.html": {
        "doi": [
            "10.1145/37402.37414",
        ],
    },
    "superscalar-cisc.html": {
        "doi": [
            "10.1109/HPCA.2006.1598111",
        ],
        "issn": [
            "1530-0897",
            "2378-203X",
        ],
    },
    "b-tree-techniques.html": {
        "doi": [
            "10.1561/1900000028",
        ],
        "url": [
            "http://dx.doi.org/10.1561/1900000028",
        ],
        "isbn": [
            "978-1-60198-482-1",
            "978-1-60198-483-8",
        ],
    },
    "real-time-rendering.html": {
        "url": [
            "https://doi.org/10.1201/9781315365459",
        ],
        "isbn": [
            "9781315365459",
        ],
    },
    "arxiv.html": {
        "url": [
            "https://arxiv.org/abs/1605.04938",
        ],
        "arxiv": [
            # identifiers after March 2007
            "arXiv:2407.13619",
            "arXiv:1608.00878",
            "arXiv:1605.04938",
            # identifiers before March 2007
            "arXiv:q-bio/0512009",
            "arXiv:math/0601009",
            "arXiv:hep-th/0512302",
            "arXiv:cond-mat/0512295",
            "arXiv:quant-ph/0511150",
        ],
    },
}

test_document_links = [
    (
        "scidb.html",
        "https://wbsg8v.xyz/d3/x/1719017408/134/i/scimag/80500000/80542000/10.1016/j.cub.2019.11.030.pdf~/Avtp6y0GwksOGlfLFy9d9Q/Parrots%20Voluntarily%20Help%20Each%20Other%20to%20Obtain%20Food%20Rewards%20--%20Brucks%2C%20D%C3%A9sir%C3%A9e%3B%20von%20Bayern%2C%20Auguste%20M_P_%20--%20Current%20Biology%2C%20%232%2C%2030%2C%20pages%20292-297_e5%2C%20--%2010_1016%2Fj_cub_2019_11_030%20--%20c28dc1242df6f931c29b9cd445a55597%20--%20Anna%E2%80%99s%20Archive.pdf",
    ),
    ("scihub.html", "https://sci.bban.top/pdf/10.1016/j.cub.2019.11.030.pdf"),
]
