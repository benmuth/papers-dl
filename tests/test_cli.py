import json
import unittest
import subprocess
import sys

test_paper_id = "10.1016/j.cub.2019.11.030"
test_paper_title = "Parrots Voluntarily Help Each Other to Obtain Food Rewards"


class TestCLI(unittest.TestCase):
    def test_parse_requires_literal_doi_period(self):
        result = subprocess.run(
            [
                sys.executable,
                "src/papers_dl.py",
                "parse",
                "-m",
                "doi",
                "-m",
                "arxiv",
                "-f",
                "jsonl",
            ],
            input="\n".join(
                [
                    "https://web.archive.org/web/20100105152318/http://www.networkcomputing.com/1119/1119f1products_5.html",
                    "https://web.archive.org/web/20110810152257/http://www.cisco.com/en/us/products/hw/modules/ps2706/ps4452/index.html",
                    "10x1002/not-a-doi 10x1021/ab123 10x1207/example&1_2",
                    "10.1016/j.cell.2024.11.027 10.1002/example 10.1021/ab123 10.1207/s123456789",
                    "arXiv:1406.5197",
                ]
            ),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.startswith("{")
        ]
        self.assertEqual(
            {record["id"] for record in records},
            {
                "10.1016/j.cell.2024.11.027",
                "10.1002/example",
                "10.1021/ab123",
                "10.1207/s123456789",
                "arXiv:1406.5197",
            },
        )

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
