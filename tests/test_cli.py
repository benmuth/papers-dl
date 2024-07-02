import unittest
import subprocess
import sys

test_paper_id = "10.1016/j.cub.2019.11.030"
test_paper_title = "Parrots Voluntarily Help Each Other to Obtain Food Rewards"


class TestCLI(unittest.TestCase):
    def test_parse_command_doi_csv(self):
        result = subprocess.run(
            [
                sys.executable,
                "src/papers_dl.py",
                "parse",
                "-m",
                "doi",
                "-p",
                "tests/documents/bsp-tree.html",
                "-f",
                "csv",
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn("10.1109/83.544569,doi", result.stdout)

    def test_parse_command_doi_jsonl(self):
        result = subprocess.run(
            [
                sys.executable,
                "src/papers_dl.py",
                "parse",
                "-m",
                "doi",
                "-f",
                "jsonl",
                "-p",
                "tests/documents/bsp-tree.html",
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn('{"id": "10.1109/83.544569", "type": "doi"}', result.stdout)

    def test_parse_command_isbn_raw(self):
        result = subprocess.run(
            [
                sys.executable,
                "src/papers_dl.py",
                "parse",
                "-m",
                "isbn",
                "-f",
                "raw",
                "-p",
                "tests/documents/b-tree-techniques.html",
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn("978-1-60198-482-1", result.stdout)
        self.assertIn("978-1-60198-483-8", result.stdout)

    def test_parse_command_cli(self):
        args = [
            sys.executable,
            "src/papers_dl.py",
            "parse",
            "-f",
            "jsonl",
            "-m",
            "isbn",
        ]

        input_data = "978-1-60198-482-1 978-1-60198-483-8"

        result = subprocess.run(args, input=input_data, capture_output=True, text=True)
        self.assertIn('{"id": "978-1-60198-482-1", "type": "isbn"}', result.stdout)
        self.assertIn('{"id": "978-1-60198-483-8", "type": "isbn"}', result.stdout)
