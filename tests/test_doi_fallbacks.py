"""Real API and CLI coverage for the DOI fallback providers."""

import os
import unittest

import aiohttp

from tests import test_open_access


class TestNewProviders(unittest.TestCase):
    fetch_paper = test_open_access.TestOpenAccessCLI.fetch_paper

    def test_biorxiv_doi(self):
        self.fetch_paper(
            "10.1101/833400", "biorxiv", "bioRxiv", "833400v2.full.pdf", 14
        )

    def test_biorxiv_explicit_version(self):
        self.fetch_paper(
            "https://www.biorxiv.org/content/10.1101/833400v1.full.pdf",
            "biorxiv",
            "bioRxiv",
            "833400v1.full.pdf",
            19,
        )

    def test_science_sleep_paper_through_unpaywall(self):
        self.fetch_paper(
            "10.1016/j.cell.2024.11.027",
            "unpaywall",
            "Norepinephrine-driven slow vasomotion",
            "nihms-2099974.pdf",
            43,
            expected_doi="10.1016/j.cell.2024.11.027",
        )

    def test_science_sleep_paper_through_pmc(self):
        self.fetch_paper(
            "10.1016/j.cell.2024.11.027",
            "pmc",
            "Norepinephrine-driven slow vasomotion",
            "nihms-2099974.pdf",
            43,
            expected_doi="10.1016/j.cell.2024.11.027",
        )

    def test_default_provider_stops_after_unpaywall(self):
        self.assertTrue(os.environ.get("UNPAYWALL_EMAIL"))
        result = self.fetch_paper(
            "10.21105/joss.01112", "all", "HRDS", "joss.01112.pdf"
        )
        self.assertNotIn("given providers: ['pmc']", result.stderr)

    def test_unpaywall_doi(self):
        self.assertTrue(
            os.environ.get("UNPAYWALL_EMAIL"), "Set UNPAYWALL_EMAIL for live API tests"
        )
        self.fetch_paper(
            "https://doi.org/10.21105/joss.01112", "unpaywall", "HRDS", "joss.01112.pdf"
        )


class TestProviderMetadata(unittest.IsolatedAsyncioTestCase):
    async def test_europepmc_pdf_metadata(self):
        from providers import europepmc

        async with aiohttp.ClientSession() as session:
            urls = await europepmc.get_urls(session, "10.1126/sciadv.1602552")
        self.assertIn("https://europepmc.org/articles/PMC5375639?pdf=render", urls)

    async def test_medrxiv_version_metadata(self):
        from providers import medrxiv

        async with aiohttp.ClientSession() as session:
            urls = await medrxiv.get_urls(session, "10.1101/2020.09.09.20191205")
        self.assertEqual(
            urls,
            ["https://www.medrxiv.org/content/10.1101/2020.09.09.20191205v2.full.pdf"],
        )

    async def test_biorxiv_does_not_claim_medrxiv_doi(self):
        from providers import biorxiv

        async with aiohttp.ClientSession() as session:
            self.assertEqual(
                await biorxiv.get_urls(session, "10.1101/2020.09.09.20191205"), []
            )

    async def test_published_doi_maps_to_medrxiv_preprint(self):
        from providers import medrxiv

        async with aiohttp.ClientSession() as session:
            urls = await medrxiv.get_urls(session, "10.1371/journal.pone.0256482")
        self.assertEqual(
            urls,
            ["https://www.medrxiv.org/content/10.1101/2021.04.29.21256344v1.full.pdf"],
        )

    async def test_manuscript_pdf_discovery_uses_pmc_dataset_xml(self):
        """Resolve the article PDF without depending on the browser landing page."""
        from providers import pmc

        requested = []
        trace = aiohttp.TraceConfig()

        async def record_request(session, context, params):
            requested.append(str(params.url))

        trace.on_request_start.append(record_request)
        async with aiohttp.ClientSession(trace_configs=[trace]) as session:
            urls = await pmc.get_urls(session, "10.1016/j.cell.2024.11.027")
        self.assertEqual(
            urls,
            ["https://pmc.ncbi.nlm.nih.gov/articles/PMC12340670/pdf/nihms-2099974.pdf"],
        )
        self.assertTrue(
            any("/PMC12340670.1/PMC12340670.1.xml" in url for url in requested),
            requested,
        )
        self.assertFalse(
            any(
                url.startswith("https://pmc.ncbi.nlm.nih.gov/articles/")
                for url in requested
            ),
            requested,
        )
