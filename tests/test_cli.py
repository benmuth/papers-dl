import unittest
import subprocess

test_paper_id= "10.1016/j.cub.2019.11.030"
test_paper_title = "Parrots Voluntarily Help Each Other to Obtain Food Rewards"

class TestPapersDLCLI(unittest.TestCase):

    def test_help_option_main(self):
        result = subprocess.run(['python', 'src/papers_dl.py', '-h'], capture_output=True, text=True)
        self.assertIn('usage: papers_dl.py [-h] {fetch,parse}', result.stdout)

    def test_help_option_fetch(self):
        result = subprocess.run(['python', 'src/papers_dl.py', 'fetch', '-h'], capture_output=True, text=True)
        self.assertIn('usage: papers_dl.py fetch [-h] [-o path] [-A USER_AGENT] (DOI|PMID|URL)', result.stdout)

    def test_help_option_parse(self):
        result = subprocess.run(['python', 'src/papers_dl.py', 'parse', '-h'], capture_output=True, text=True)
        self.assertIn('usage: papers_dl.py parse [-h] [-m type] [-f [fmt]] path', result.stdout)

    # def test_fetch_command_doi(self):
    #     result = subprocess.run(['python', 'src/papers_dl.py', 'fetch', test_paper_id], capture_output=True, text=True)
    #     self.assertIn(test_paper_title, result.stdout)

    def test_parse_command_doi_csv(self):
        result = subprocess.run(['python', 'src/papers_dl.py', 'parse', '-m', 'doi', 'tests/identifiers/bsp-tree.html', '-f', 'csv'], capture_output=True, text=True)
        self.assertIn('doi,10.1109/83.544569', result.stdout)

    def test_parse_command_isbn_jsonl(self):
        result = subprocess.run(['python', 'src/papers_dl.py', 'parse', '-m', 'isbn', 'tests/identifiers/bsp-tree.html', '-f', 'jsonl'], capture_output=True, text=True)
        self.assertIn('{"id": "37265733000", "type": "isbn"}', result.stdout)

