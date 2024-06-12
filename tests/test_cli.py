import unittest
import subprocess

test_paper_id = "10.1016/j.cub.2019.11.030"
test_paper_title = "Parrots Voluntarily Help Each Other to Obtain Food Rewards"


class TestCLI(unittest.TestCase):
    def test_parse_command_doi_csv(self):
        result = subprocess.run(
            [
                "python",
                "src/papers_dl.py",
                "parse",
                "-m",
                "doi",
                "-p",
                "tests/identifiers/bsp-tree.html",
                "-f",
                "csv",
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn("10.1109/83.544569,doi", result.stdout)

    def test_parse_command_isbn_jsonl(self):
        result = subprocess.run(
            [
                "python",
                "src/papers_dl.py",
                "parse",
                "-m",
                "isbn",
                "-f",
                "jsonl",
                "-p",
                "tests/identifiers/bsp-tree.html",
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn('{"id": "6419400074", "type": "isbn"}', result.stdout)
        self.assertIn('{"id": "1558153217", "type": "isbn"}', result.stdout)
