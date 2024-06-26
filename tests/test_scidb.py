import unittest

from fetch.fetch_utils import find_pdf_url

# test_dir = "tests/"

test_cases = [
    (
        "scidb.html",
        "https://wbsg8v.xyz/d3/x/1719017408/134/i/scimag/80500000/80542000/10.1016/j.cub.2019.11.030.pdf~/Avtp6y0GwksOGlfLFy9d9Q/Parrots%20Voluntarily%20Help%20Each%20Other%20to%20Obtain%20Food%20Rewards%20--%20Brucks%2C%20D%C3%A9sir%C3%A9e%3B%20von%20Bayern%2C%20Auguste%20M_P_%20--%20Current%20Biology%2C%20%232%2C%2030%2C%20pages%20292-297_e5%2C%20--%2010_1016%2Fj_cub_2019_11_030%20--%20c28dc1242df6f931c29b9cd445a55597%20--%20Anna%E2%80%99s%20Archive.pdf",
    ),
    ("scihub.html", "https://sci.bban.top/pdf/10.1016/j.cub.2019.11.030.pdf"),
]


class TestSciDB(unittest.TestCase):
    # Not sure if we should be making requests to download from scidb in tests
    # def test_fetch_doi(self):
    #     sess = requests.Session()
    #     path = fetch("10.1016/j.cub.2019.11.030", sess)
    #     # print(path)
    #     self.assertIsNotNone(path)

    def test_find_pdf_in_html(self):
        for file, expected_url in test_cases:
            with open(file, "rt") as f:
                html_content = f.read()
                pdf_url = find_pdf_url(html_content)
            self.assertEqual(pdf_url, expected_url)
