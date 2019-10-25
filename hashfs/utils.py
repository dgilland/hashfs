# -*- coding: utf-8 -*-

import os


def compact(items):
    """Return only truthy elements of `items`."""
    return [item for item in items if item]


def issubdir(subpath, path):
    """Return whether `subpath` is a sub-directory of `path`."""
    # Append os.sep so that paths like /usr/var2/log doesn't match /usr/var.
    path = os.path.realpath(path) + os.sep
    subpath = os.path.realpath(subpath)
    return subpath.startswith(path)


def shard(digest, depth, width):
    # This creates a list of `depth` number of tokens with width
    # `width` from the first part of the id plus the remainder.
    return compact(
        [digest[i * width : width * (i + 1)] for i in range(depth)]
        + [digest[depth * width :]]
    )
