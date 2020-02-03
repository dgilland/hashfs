"""Utilities for sharding etc."""

import hashlib
import io
import os
from collections import namedtuple
from typing import Any, List, Optional, Union

import fs as pyfs
from absl import logging
from fs.base import FS


def compact(items: List[Optional[Any]]) -> List[Any]:
    """Return only truthy elements of `items`."""
    return [item for item in items if item]


def to_bytes(item: Union[str, bytes]) -> bytes:
    """Accepts either a bytes instance or a string; if str, returns a bytes
  instance, else acts as identity.

  """
    ret = item

    if not isinstance(item, bytes):
        ret = bytes(item, "utf8")

    return ret


def computehash(stream, algorithm: hashlib.algorithms_available) -> str:
    """Compute hash of file using the supplied `algorithm`."""
    hashobj = hashlib.new(algorithm)
    for data in stream:
        hashobj.update(to_bytes(data))
    return hashobj.hexdigest()


def shard(digest: str, depth: int, width: int) -> str:
    """This creates a list of `depth` number of tokens with width `width` from the
  first part of the id plus the remainder.

  TODO examine Clojure's Blocks to see if there's some nicer style here.

  """

    first = [digest[i * width:width * (i + 1)] for i in range(depth)]
    remaining = [digest[depth * width:]]
    return compact(first + remaining)


def load_fs(root: Union[FS, str]) -> FS:
    """If str is supplied, returns an instance of OSFS, backed by the filesystem."""
    if isinstance(root, str):
        return pyfs.open_fs(root)

    if isinstance(root, FS):
        return root

    raise Exception("Not a filesystem or path!")


def syspath(fs: FS, path: str) -> Optional[str]:
    """"""
    try:
        return fs.getsyspath(path)
    except pyfs.errors.NoSysPath:
        logging.error("Can't get a path.")


# TODO add the hash here
# TODO add a to and from string method
class HashAddress(namedtuple("HashAddress", ["id", "relpath", "is_duplicate"])):
    """File address containing file's path on disk and it's content hash ID.

    Attributes:
        id (str): Hash ID (hexdigest) of file contents.
        relpath (str): Relative path location to :attr:`HashFS.root`.
        is_duplicate (boolean, optional): Whether the hash address created was
            a duplicate of a previously existing file. Can only be ``True``
            after a put operation. Defaults to ``False``.
    """

    def __new__(cls, id, relpath, is_duplicate=False):
        return super(HashAddress, cls).__new__(cls, id, relpath, is_duplicate)

    def __eq__(self, obj):
        return isinstance(obj, HashAddress) and \
          obj.id == self.id and \
          obj.relpath == self.relpath


# TODO examine, allow this to handle wrapping another stream in addition to itself.
class Stream(object):
    """Common interface for file-like objects.

    The input `obj` can be a file-like object or a path to a file. If `obj` is
    a path to a file, then it will be opened until :meth:`close` is called.
    If `obj` is a file-like object, then it's original position will be
    restored when :meth:`close` is called instead of closing the object
    automatically. Closing of the stream is deferred to whatever process passed
    the stream in.

    Successive readings of the stream is supported without having to manually
    set it's position back to ``0``.
    """

    def __init__(self, obj, fs: Optional[FS] = None):
        if hasattr(obj, "read"):
            pos = obj.tell()
        elif fs:
            if fs.isfile(obj):
                obj = fs.open(obj, "rb")
                pos = None
            else:
                raise ValueError(
                    "Object must be a valid file path or a readable object")
        else:
            raise ValueError(
                "Object must be readable, OR you must supply a filesystem.")

        try:
            file_stat = fs.getinfo(obj.name, namespaces=['stat'])
            buffer_size = file_stat.st_blksize
        except Exception:
            buffer_size = 8192

        self._obj = obj
        self._pos = pos
        self._buffer_size = buffer_size

    def __iter__(self):
        """Read underlying IO object and yield results. Return object to
        original position if we didn't open it originally.
        """
        self._obj.seek(0)

        while True:
            data = self._obj.read(self._buffer_size)

            if not data:
                break

            yield data

        if self._pos is not None:
            self._obj.seek(self._pos)

    def close(self):
        """Close underlying IO object if we opened it, else return it to
        original position.
        """
        if self._pos is None:
            self._obj.close()
        else:
            self._obj.seek(self._pos)
