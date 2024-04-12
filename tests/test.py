# from src.scihub import SciHub
import unittest
import requests


class TestSciHub(unittest.TestCase):
    def test_scihub_up(self):
        url = "https://sci-hub.now.sh/"    
        response = requests.get(url)
        self.assertEqual(response.status_code, 200, f"Expected status code 200, but got {response.status_code}")
