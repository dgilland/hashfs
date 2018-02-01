# -*- coding: utf-8 -*-
# flake8: noqa
"""Python 2/3 compatibility
"""

import sys
import os
import os.path

try:
    # Python >= 3.5.
    from os import scandir, walk
except ImportError:
    try:
        # Back ported scandir package.
        from scandir import scandir, walk
    except ImportError:
        # Back ported package not installed so fallback to baseline.
        from os import walk
        scandir = None

if scandir:
    def list_dir_files(path):
        it = scandir(path)
        try:
            for file in it:
                if file.is_file():
                    yield file.path
        finally:
            try:
                it.close()
            except AttributeError:
                pass
else:
    def list_dir_files(path):
        for file in os.listdir(path):
            file = os.path.join(path, file)
            if os.path.isfile(file):
                yield file



PY3 = sys.version_info[0] == 3


if PY3:
    text_type = str
    string_types = (str,)

    def to_bytes(text):
        if not isinstance(text, bytes):
            text = bytes(text, 'utf8')
        return text
else:
    text_type = unicode
    string_types = (str, unicode)

    def to_bytes(text):
        if not isinstance(text, string_types):
            text = text_type(text)
        return text


try:
    is_callable = callable
except:
    def is_callable(fn):
        return hasattr(fn, '__call__')
