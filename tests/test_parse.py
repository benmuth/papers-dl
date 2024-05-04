from src.parse import parse_ids_from_text, id_patterns
import unittest
import os

target_ids = ("doi", "pmid", "isbn", "issn", "url")

class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_material_dir = "tests/identifiers"
        cls.valid_id_types = id_patterns.keys()
        for id_type in target_ids:
            if id_type not in cls.valid_id_types:
                print(f"Skipping testing for {id_type} parsing!")

    def test_parse_text(self):
        """
            Test to parse identifiers from arbitrary text.
        """
        for file in test_document_ids:
            with open(os.path.join(TestParser.test_material_dir, file)) as f:
                file_content = f.read()
            for id_type in TestParser.valid_id_types:
                parsed_ids = parse_ids_from_text(file_content, id_type)
                expected_ids = test_document_ids[file].get(id_type)
                if not expected_ids:
                    continue

                parsed_ids = [id[1] for id in parsed_ids]
                for expected_id in expected_ids:
                    self.assertIn(
                        expected_id,
                        parsed_ids,
                        f"ID {expected_id} not found in {file} for ID type {id_type}",
                    )

test_document_ids = {
    "ids.txt": {
        "url": ["https://www.cell.com/current-biology/fulltext/S0960-9822(19)31469-1"],
        "doi": ["10.1016/j.cub.2019.11.030"],
    },
    "bsp-tree.html": {
        "doi": ["10.1109/83.544569"],
        "issn": ["1057-7149", "1941-0042"],
    },
    "reyes-rendering.html": {
        "doi": ["10.1145/37402.37414"],
        "url": [
            "https://dl.acm.org/doi/10.1145/3603521.3604289",
            "https://doi.org/10.1145/3596711.3596742",
            "https://doi.org/10.1145/37402.37414",
        ],
    },
    "superscalar-cisc.html": {
        "doi": ["10.1109/HPCA.2006.1598111"],
        "issn": ["1530-0897", "2378-203X"],
    },
    "b-tree-techniques.html": {
        "doi": ["10.1561/1900000028"],
        "url": ["http://dx.doi.org/10.1561/1900000028"],
        "isbn": ["978-1-60198-482-1", "978-1-60198-483-8"],
    },
    "real-time-rendering.html": {
        "url": ["https://doi.org/10.1201/9781315365459"],
        "isbn": ["9781315365459"],
    },
}
