# Overview
`papers-dl` is a command line application for downloading scientific papers.

## Usage
```shell
# parse DOI identifiers from a file:
papers-dl parse --match doi --path pages/my-paper.html

# fetch given identifier from SciHub:
papers-dl fetch "10.1016/j.cub.2019.11.030"
```

This project started as a fork of [scihub.py](https://github.com/zaytoun/scihub.py).
