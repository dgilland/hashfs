# -*- coding: utf-8 -*-
# flake8: noqa
"""Python 2/3 compatibility
"""

import sys

try:
    # Python >= 3.5.
    from os import scandir
except ImportError:
    try:
        # Back ported scandir package.
        from scandir import scandir
    except ImportError:
        # Back ported package not installed so fallback to baseline.
        scandir = None

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    string_types = (str,)
    FileExistsError = FileExistsError

    def to_bytes(text):
        if not isinstance(text, bytes):
            text = bytes(text, "utf8")
        return text

else:
    text_type = unicode
    string_types = (str, unicode)
    FileExistsError = OSError

    def to_bytes(text):
        if not isinstance(text, string_types):
            text = text_type(text)
        return text
