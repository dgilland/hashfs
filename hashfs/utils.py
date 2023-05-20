# -*- coding: utf-8 -*-


"""
common utils for hashfs
"""


import os
from pathlib import Path
from typing import List


def compact(items):
    """Return only truthy elements of `items`."""
    return [item for item in items if item]


def issubdir(subpath, path):
    """Return whether `subpath` is a sub-directory of `path`."""
    # Append os.sep so that paths like /usr/var2/log doesn't match /usr/var.
    path = os.path.realpath(path) + os.sep
    subpath = os.path.realpath(subpath)
    return subpath.startswith(path)


def shard(digest, depth, width) -> List[str]:
    # This creates a list of `depth` number of tokens with width
    # `width` from the first part of the id plus the remainder.
    return compact(
        [digest[i * width : width * (i + 1)] for i in range(depth)]
        + [digest[depth * width :]]
    )


def create_hex_directory(directory: Path,
                         width: int,
                         mode: int):
    """
    create 16 ** width directories in the directory.

    Args:
        directory: the parent director
        width: the name width of each subdirecory
    """
    for i in range(16**width):
        sub_dir = directory.joinpath(
            f'{i:0{width}x}'
        )
        sub_dir.mkdir(parents=True, exist_ok=True, mode=mode)
