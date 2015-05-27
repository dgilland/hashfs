
from collections import namedtuple
from contextlib import contextmanager, closing
from distutils.dir_util import mkpath  # pylint: disable=no-name-in-module
import glob
import hashlib
import io
import os
import shutil
from tempfile import NamedTemporaryFile

from .utils import walkfiles, compact
from ._compat import to_bytes


class Shed(object):
    """Content addressable file manager.

    Args:
        root (str): Directory path used as root of storage space.
        depth (int, optional): Number of folders to create when saving a file.
            Defaults to ``4``.
        length (int): Number of characters each subfolder will contain.
            Defaults to ``1``.
        algorithm (str): Hash algorithm to use when computing file hash.
            Algorithm should be available in ``hashlib`` module. Defaults to
            ``'sha256'``.
        fmode (int, optional): File mode permission to set when adding files to
            directory. Defaults to ``0o664`` which allows owner/group to
            read/write and everyone else to read.
        dmode (int, optional): Directory mode permission to set for
            subdirectories. Defaults to ``0o755`` which allows owner/group to
            read/write and everyone else to read and everyone to execute.
    """
    def __init__(self,
                 root,
                 depth=4,
                 length=1,
                 algorithm='sha256',
                 fmode=0o664,
                 dmode=0o755):
        self.root = os.path.realpath(root)
        self.fmode = fmode
        self.dmode = dmode
        self.depth = depth
        self.length = length
        self.algorithm = algorithm

        self.makepath(self.root)

    def put(self, obj, extension=None):
        """Store contents of `obj` on disk using its content hash for the
        address.
        """
        stream = Stream(obj)
        digest = self.computehash(stream)

        with closing(stream):
            filepath = self.copy(stream, digest, extension)

        return Address(filepath, digest)

    def files(self):
        """Return generator that yields all files under :attr:`root` directory.
        """
        return walkfiles(self.root)

    def exists(self, digest):
        """Check whether a given file digest exsists on disk."""
        path = self.filepath(digest)
        # Match using exact path or glob with wildcard extension.
        return os.path.isfile(path) or glob.glob(path + '.*')

    def makepath(self, path):
        """Physically create the folder path on disk."""
        mkpath(path, mode=self.dmode)

    def copy(self, stream, digest, extension=None):
        """Copy the contents of `stream` onto disk with an optional file
        extension appended. The copy process using a temporary file to store
        the initial contents and then moves this file to it's final location.
        """
        filepath = self.filepath(digest, extension)

        if not os.path.isfile(filepath):
            with tmpfile(stream, self.fmode) as fname:
                self.makepath(os.path.dirname(filepath))
                shutil.copy(fname, filepath)

        return filepath

    def computehash(self, stream):
        """Compute hash of file using :attr:`algorithm`."""
        hash = hashlib.new(self.algorithm)
        for data in stream:
            hash.update(to_bytes(data))
        return hash.hexdigest()

    def filepath(self, digest, extension=''):
        """Build the file path for a given hash digest. Optionally, append a
        file extension.
        """
        paths = self.tokenize(digest)

        if extension and not extension.startswith(os.extsep):
            extension = os.extsep + extension
        elif not extension:
            extension = ''

        return os.path.join(self.root, *paths) + extension

    def tokenize(self, id):
        """Convert content ID into tokens that will become the folder tree
        structure.
        """
        # This creates a list of `depth` number of tokens with length
        # `length` from the first part of the digest plus the remainder.
        return compact([id[i * self.length:self.length * (i + 1)]
                        for i in range(self.depth)] +
                       [id[self.depth * self.length:]])


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
    def __init__(self, obj):
        if hasattr(obj, 'read'):
            pos = obj.tell()
        elif os.path.isfile(obj):
            obj = io.open(obj, 'rb')
            pos = None
        else:
            raise ValueError(('Object must be a valid file path or '
                              'a readable object.'))

        self._obj = obj
        self._pos = pos

    def __iter__(self):
        """Read underlying IO object and yield results. Return object to
        original position if we didn't open it originally.
        """
        self._obj.seek(0)

        while True:
            data = self._obj.read()

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


class Address(namedtuple('Address', ['path', 'digest'])):
    """File Address containing file's path on disk and it's content hash."""
    pass


@contextmanager
def tmpfile(stream, mode=None):
    """Context manager that writes a :class:`Stream` object to a named
    temporary file and yield it's filename. Cleanup deletes from the temporary
    file from disk.

    Args:
        stream (Stream): Stream object to write to disk as temporary file.
        mode (int, optional): File mode to set on temporary file.

    Returns:
        str: Temporoary file name
    """
    tmp = NamedTemporaryFile(delete=False)

    if mode is not None:
        oldmask = os.umask(0)

        try:
            os.chmod(tmp.name, mode)
        finally:
            os.umask(oldmask)

    for data in stream:
        tmp.write(to_bytes(data))

    tmp.close()

    yield tmp.name

    os.remove(tmp.name)
