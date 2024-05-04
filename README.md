# Overview
`papers-dl` is a command line application for downloading scientific papers.

## Usage
```
usage: papers_dl.py [-h] {fetch,parse} ...

Download scientific papers from the command line

positional arguments:
  {fetch,parse}
    fetch        try to download a paper with the given identifier
    parse        parse identifiers from a file

options:
  -h, --help     show this help message and exit  

# fetch
usage: papers_dl.py fetch [-h] [-o path] [-A USER_AGENT]
                          (DOI|PMID|URL)

positional arguments:
  (DOI|PMID|URL)        the identifier to try to download

options:
  -h, --help            show this help message and exit
  -o path, --output path
                        optional output directory for downloaded
                        papers
  -A USER_AGENT, --user-agent USER_AGENT

# parse
usage: papers_dl.py parse [-h] [-m type] [-f [fmt]] path

positional arguments:
  path                  the path of the file to parse

options:
  -h, --help            show this help message and exit
  -m type, --match type
                        the type of identifier to match
  -f [fmt], --format [fmt]
                        the output format for printing
```

This project started as a impromptu fork of [scihub.py](https://github.com/zaytoun/scihub.py).
