# Overview
`papers-dl` is a command line application for downloading scientific papers.

## Usage

`python papers-dl.py -d <DOI|URL> -o <output directory>`

or

`python papers-dl.py -f <text file with newline separated DOIs|URLs> -o <output directory>`

It should either

- download the paper directly identified by the DOI or URL you gave it
- if you gave it a URL but it can't directly find a paper through it, then it will parse the page's HTML for DOIs and attempt to download all DOIs that are found.

In the second case, we can probably be smarter about only downloading the DOIs intended (based on title or something?), but it's pretty dumb right now.

This project includes a modified version of [scihub.py](https://github.com/zaytoun/scihub.py).
