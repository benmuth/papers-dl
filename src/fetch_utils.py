import json
import logging
import os

from pdf2doi import pdf2doi
import hashlib


def generate_name(res):
    """
    Generate unique filename for paper by calcuating md5 hash of file
    contents.
    """
    pdf_hash = hashlib.md5(res.content).hexdigest()
    return f"{pdf_hash}" + ".pdf"


def rename(out_dir, path, name=None) -> str:
    """
    Renames a PDF to either the given name or its appropriate title, if
    possible. Adds the PDF extension. Returns the new path if renaming was
    successful, or the original path if not.
    """

    logging.info("Finding paper title")
    pdf2doi.config.set("verbose", False)

    #
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
