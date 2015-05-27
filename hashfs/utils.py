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


def walk(path,
         folders=True,
         files=True,
         topdown=True,
         onerror=None,
         followlinks=False):
    """Recursively walk `path` yielding folders and files if ``folders==True``
    and/or ``files==True`` respectively.
    """
    for folder, subfolders, folder_files in os.walk(path,
                                                    topdown=topdown,
                                                    onerror=onerror,
                                                    followlinks=followlinks):
        if folders:
            yield os.path.abspath(folder)

        if files:
            for file_ in folder_files:
                yield os.path.abspath(os.path.join(folder, file_))


def walkfolders(path, topdown=True, onerror=None, followlinks=False):
    """Recursively walk `path` and yield folders."""
    return walk(path,
                folders=True,
                files=False,
                topdown=True,
                onerror=None,
                followlinks=False)


def walkfiles(path, topdown=True, onerror=None, followlinks=False):
    """Recursively walk `path` and yield files."""
    return walk(path,
                folders=False,
                files=True,
                topdown=True,
                onerror=None,
                followlinks=False)
