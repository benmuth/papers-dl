# Overview
`papers-dl` is a command line application for downloading scientific papers.

## Usage
```
usage: papers-dl.py [-h] {fetch,parse} ...

Download scientific papers from the command line

positional arguments:
  {fetch,parse}
    fetch        try to download a paper from the given
                 query
    parse        parse identifiers from a file

options:
  -h, --help     show this help message and exit
  
# fetch
usage: papers-dl.py fetch [-h] [-o path] (DOI|PMID|URL)

positional arguments:
  (DOI|PMID|URL)        the identifier to try to download

options:
  -h, --help            show this help message and exit
  -o path, --output path
                        optional output directory for
                        downloaded papers

# parse
usage: papers-dl.py parse [-h] [-m type] path

positional arguments:
  path                  the path of the file to parse

options:
  -h, --help            show this help message and exit
  -m type, --match type
                        the type of identifier to match
```
This project includes a modified version of [scihub.py](https://github.com/zaytoun/scihub.py).
