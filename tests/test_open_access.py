"""Integration tests against real publisher and NLM open-access services."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

from fetch.fetch import rename


class TestOpenAccessCLI(unittest.TestCase):
    def fetch_paper(
        self,
        identifier,
        provider,
        expected_text,
        expected_source,
        expected_pages=None,
        text_page=0,
        env=None,
        expected_doi=None,
        expected_filename=None,
    ):
        with tempfile.TemporaryDirectory() as output:
            result = subprocess.run(
                [
                    sys.executable,
                    "src/papers_dl.py",
                    "--verbose",
                    "fetch",
                    "--providers",
                    provider,
                    "--output",
                    output,
                    identifier,
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Successfully downloaded", result.stdout, result.stderr)
            self.assertIn(expected_source, result.stdout)
            files = list(Path(output).glob("*.pdf"))
            self.assertEqual(len(files), 1, result.stdout)
            self.assertTrue(files[0].read_bytes().startswith(b"%PDF-"))
            if expected_filename is not None:
                self.assertEqual(files[0].name, expected_filename)
            with fitz.open(files[0]) as paper:
                self.assertGreater(paper.page_count, 0)
                if expected_pages is not None:
                    self.assertEqual(paper.page_count, expected_pages)
                self.assertIn(expected_text, paper[text_page].get_text())
                if expected_doi:
                    self.assertIn(expected_doi, paper[0].get_text())
            return result

    def test_title_rename_preserves_pdf_bytes_and_output_directory(self):
        with tempfile.TemporaryDirectory() as output:
            original = Path(output) / "paper.pdf"
            with fitz.open() as paper:
                page = paper.new_page()
                page.insert_text((72, 72), "Real PDF rename preservation")
                paper.save(original)
            content = original.read_bytes()
            renamed = Path(
                rename(output, str(original), "Ca<sup>2+</sup> &amp; Na/K \\ channels")
            )
            self.assertEqual(renamed, Path(output) / "Ca2+ & Na_K _ channels.pdf")
            self.assertFalse(original.exists())
            self.assertEqual(renamed.read_bytes(), content)
            self.assertEqual(list(Path(output).iterdir()), [renamed])
            with fitz.open(renamed) as paper:
                self.assertEqual(paper.page_count, 1)
                self.assertIn("Real PDF rename preservation", paper[0].get_text())

    def test_long_titles_keep_distinct_complete_pdfs_in_portable_filenames(self):
        titles = [
            "Potential benefit of retrospective use of neutron monitors in improving "
            "ionising radiation exposure assessment on international flights: issues "
            "raised by neutron passive dosimeter measurements and EPCARD simulations "
            "during sudden changes in solar activity",
            "研究結果" * 90 + " first paper",
            "研究結果" * 90 + " second paper",
        ]
        with tempfile.TemporaryDirectory() as output:
            saved = {}
            for index, title in enumerate(titles):
                original = Path(output) / f"source-{index}.pdf"
                with fitz.open() as paper:
                    page = paper.new_page()
                    page.insert_text((72, 72), f"Complete paper {index}")
                    paper.save(original)
                content = original.read_bytes()
                renamed = Path(rename(output, str(original), title))
                self.assertNotEqual(renamed, original)
                self.assertEqual(renamed.parent, Path(output))
                self.assertLessEqual(len(renamed.name.encode("utf-8")), 255)
                self.assertTrue(renamed.name.startswith(title[:10]))
                self.assertEqual(renamed.suffix, ".pdf")
                self.assertNotIn(renamed, saved)
                self.assertFalse(original.exists())
                saved[renamed] = content
                with fitz.open(renamed) as paper:
                    self.assertEqual(paper.page_count, 1)
                    self.assertIn(f"Complete paper {index}", paper[0].get_text())
            self.assertEqual(set(Path(output).iterdir()), set(saved))
            for path, content in saved.items():
                self.assertEqual(path.read_bytes(), content)

    def test_known_doi_titles_pdf_without_embedded_identifier(self):
        self.fetch_paper(
            "10.1086/322460",
            "unpaywall",
            "Timescale Stretch Parameterization",
            "https://arxiv.org/pdf/astro-ph/0104382",
            expected_filename=(
                "Timescale Stretch Parameterization of Type Ia "
                "SupernovaB‐Band Light Curves.pdf"
            ),
            env={**os.environ, "UNPAYWALL_EMAIL": "unpaywall-papersdl@archivebox.io"},
        )

    def test_pmc_title_html_is_plain_filename(self):
        self.fetch_paper(
            "10.1038/sj.bjp.0705942",
            "pmc",
            "Intravenous anaesthetics",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC1575970/pdf/144-0705942a.pdf",
            expected_filename=(
                "Intravenous anaesthetics inhibit nicotinic acetylcholine "
                "receptor‐mediated currents and Ca2+ transients in rat "
                "intracardiac ganglion neurons.pdf"
            ),
        )

    def test_default_provider_downloads_open_access_doi(self):
        self.fetch_paper(
            "10.1126/sciadv.1602552",
            "all",
            "Microbial arms race",
            "https://pmc-oa-opendata.s3.amazonaws.com/",
            env={**os.environ, "UNPAYWALL_EMAIL": ""},
        )

    def test_pmc_resolves_doi_url(self):
        self.fetch_paper(
            "https://doi.org/10.1126/sciadv.1602552",
            "pmc",
            "Microbial arms race",
            "https://pmc-oa-opendata.s3.amazonaws.com/",
        )

    def test_publisher_resolves_doi(self):
        self.fetch_paper(
            "10.21105/joss.01112",
            "publisher",
            "HRDS",
            "https://joss.theoj.org/papers/10.21105/joss.01112.pdf",
        )

    def test_publisher_resolves_landing_page(self):
        self.fetch_paper(
            "https://joss.theoj.org/papers/10.21105/joss.01112",
            "publisher",
            "HRDS",
            "https://joss.theoj.org/papers/10.21105/joss.01112.pdf",
        )

    def test_publisher_discovers_pdf_without_pdf_extension(self):
        self.fetch_paper(
            "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0185809",
            "publisher",
            "More than 75 percent decline",
            "https://journals.plos.org/plosone/article/file?",
        )

    def test_pmc_resolves_pubmed_id_for_another_journal(self):
        self.fetch_paper(
            "23193287",
            "pmc",
            "GenBank",
            "https://pmc-oa-opendata.s3.amazonaws.com/PMC3531190.1/",
        )

    def test_default_provider_accepts_pubmed_id(self):
        self.fetch_paper(
            "23193287",
            "all",
            "GenBank",
            "https://pmc-oa-opendata.s3.amazonaws.com/PMC3531190.1/",
        )

    def test_pmc_discovers_available_version_without_version_one(self):
        self.fetch_paper(
            "PMC1193645",
            "pmc",
            "Impaired Development",
            "https://pmc-oa-opendata.s3.amazonaws.com/PMC1193645.2/",
        )

    def test_pmc_honors_explicit_version(self):
        self.fetch_paper(
            "PMC1193645.2",
            "pmc",
            "Impaired Development",
            "https://pmc-oa-opendata.s3.amazonaws.com/PMC1193645.2/",
        )

    def test_pmc_does_not_substitute_an_unavailable_explicit_version(self):
        with tempfile.TemporaryDirectory() as output:
            result = subprocess.run(
                [
                    sys.executable,
                    "src/papers_dl.py",
                    "--verbose",
                    "fetch",
                    "--providers",
                    "pmc",
                    "--output",
                    output,
                    "PMC1193645.1",
                ],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No papers found", result.stdout, result.stderr)
            self.assertEqual(list(Path(output).iterdir()), [])

    def test_zenodo_record_url(self):
        self.fetch_paper(
            "https://zenodo.org/records/13886268",
            "zenodo",
            "The Barts Health Data Platform",
            "zenodo.org/api/records/",
            7,
        )

    def test_zenodo_doi(self):
        self.fetch_paper(
            "10.5281/zenodo.13886268",
            "zenodo",
            "The Barts Health Data Platform",
            "zenodo.org/api/records/",
            7,
        )

    def test_figshare_institutional_doi(self):
        self.fetch_paper(
            "10.25405/ncl.34202931.v1",
            "figshare",
            "Load shortening characteristics",
            "amazonaws.com/",
            28,
        )

    def test_figshare_institutional_url(self):
        self.fetch_paper(
            "https://outputs.ncl.ac.uk/articles/journal_contribution/Load_shortening_characteristics_of_marine_grade_aluminium_alloy_plates_in_longitudinal_compression/34202931",
            "figshare",
            "Load shortening characteristics",
            "amazonaws.com/",
            28,
        )

    def test_ntrs_citation_url(self):
        self.fetch_paper(
            "https://ntrs.nasa.gov/citations/20170009584",
            "ntrs",
            "Web Accessible API",
            "ntrs.nasa.gov/api/citations/",
            44,
        )

    def test_ntrs_identifier(self):
        self.fetch_paper(
            "ntrs:20170009584",
            "ntrs",
            "Web Accessible API",
            "ntrs.nasa.gov/api/citations/",
            44,
        )

    def test_osti_record_url(self):
        self.fetch_paper(
            "https://www.osti.gov/biblio/3413920",
            "osti",
            "Modeling and Predicting Lignin",
            "osti.gov/servlets/purl/",
            23,
            text_page=1,
        )

    def test_osti_doi(self):
        self.fetch_paper(
            "10.2172/3413920",
            "osti",
            "Modeling and Predicting Lignin",
            "osti.gov/servlets/purl/",
            23,
            text_page=1,
        )

    def test_hal_landing_url(self):
        self.fetch_paper(
            "https://amu.hal.science/hal-01232674v1",
            "hal",
            "EN TORNO A LA CULTURA",
            "hal.science/",
            27,
        )

    def test_hal_explicit_version(self):
        self.fetch_paper(
            "hal-01232674v1", "hal", "EN TORNO A LA CULTURA", "hal.science/", 27
        )

    def test_hal_older_version(self):
        self.fetch_paper(
            "hal-03184936v1",
            "hal",
            "https://hal.science/hal-03184936v1",
            "hal.science/hal-03184936v1/document",
            11,
        )


if __name__ == "__main__":
    unittest.main()
