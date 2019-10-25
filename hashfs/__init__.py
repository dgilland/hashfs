# -*- coding: utf-8 -*-
"""HashFS is a content-addressable file management system. What does that mean?
Simply, that HashFS manages a directory where files are saved based on the
file's hash.

Typical use cases for this kind of system are ones where:

- Files are written once and never change (e.g. image storage).
- It's desirable to have no duplicate files (e.g. user uploads).
- File metadata is stored elsewhere (e.g. in a database).
"""

from .__meta__ import (
    __title__,
    __summary__,
    __url__,
    __version__,
    __author__,
    __email__,
    __license__,
)

from .hashfs import HashFS, HashAddress


__all__ = ("HashFS", "HashAddress")
