import hashlib
import json
import logging
import os
import re

import pdf2doi
from bs4 import BeautifulSoup


def save(data, path):
    """
    Save a file give data and a path.
    """
    try:
        logging.info(f"Saving file to {path}")

        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        logging.error(f"Failed to write to {path} {e}")
        raise e


def find_pdf_url(html_content) -> str | None:
    """
    Given HTML content, find an embedded link to a PDF. Returns None if
    nothing is found
    """

    s = BeautifulSoup(html_content, "html.parser")

    # look for a dynamically loaded PDF
    script_element = s.find("script", string=re.compile("PDFObject.embed"))

    if script_element:
        match = re.search(r'PDFObject\.embed\("([^"]+)"', script_element.string)
        if match:
            logging.info(f"found dynamically loaded PDF: {script_element}")
            return match.group(1)

    # look for the "<embed>" element (scihub)
    embed_element = s.find("embed", {"id": "pdf", "type": "application/pdf"})

    if embed_element:
        # direct_url = embed_element["src"]
        direct_url = embed_element["src"]
        if direct_url:
            logging.info(f"found embedded PDF: {embed_element}")
            return direct_url

    # look for an iframe
    iframe = s.find("iframe", {"type": "application/pdf"})

    # src = None
    if iframe:
        logging.info(f"found iframe: {iframe}")
        direct_url = iframe.get("src")
        if direct_url:
            logging.info(f"found iframe: {iframe}")
            return direct_url

    logging.info("No direct link to PDF found")
    return None


def generate_name(content):
    "Generate unique filename for paper"

    pdf_hash = hashlib.md5(content).hexdigest()
    return f"{pdf_hash}" + ".pdf"


def rename(out_dir, path, name=None) -> str:
    """
    Renames a PDF to either the given name or its appropriate title, if
    possible. Adds the PDF extension. Returns the new path if renaming was
    successful, or the original path if not.
    """

    logging.info("Finding paper title")
    pdf2doi.config.set("verbose", False)

    try:
        if name is None:
            result_info = pdf2doi.pdf2doi(path)
            validation_info = json.loads(result_info["validation_info"])
            name = validation_info.get("title")

        if name:
            name += ".pdf"
            new_path = os.path.join(out_dir, name)
            os.rename(path, new_path)
            logging.info(f"File renamed to {new_path}")
            return new_path
        else:
            return path
    except Exception as e:
        logging.error(f"Couldn't get paper title from PDF at {path}: {e}")
        return path
