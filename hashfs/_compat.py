# -*- coding: utf-8 -*-
# pylint: skip-file
"""Python 2/3 compatibility
"""

import sys


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
