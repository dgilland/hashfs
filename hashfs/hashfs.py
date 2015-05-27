
from collections import namedtuple
from contextlib import contextmanager, closing
from distutils.dir_util import mkpath  # pylint: disable=no-name-in-module
import glob
import hashlib
import io
import os
import shutil
from tempfile import NamedTemporaryFile

from .utils import compact, issubdir
from ._compat import to_bytes


class HashFS(object):
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

        with closing(stream):
            id = self.computehash(stream)
            filepath = self.copy(stream, id, extension)

        return Address(id, filepath)

    def get(self, id_or_path, mode='rb'):
        """Return fileobj from given id or path."""
        realpath = self.realpath(id_or_path)
        if realpath is None:
            raise IOError('Could not locate file: {0}'.format(id_or_path))

        return io.open(realpath, mode)

    def delete(self, id_or_path):
        """Delete file using id or path. Remove any empty directories after
        deleting.
        """
        realpath = self.realpath(id_or_path)
        if realpath is None:
            return

        try:
            os.remove(realpath)
        except OSError:  # pragma: no cover
            pass
        else:
            self.remove_empty(os.path.dirname(realpath))

    def remove_empty(self, subpath):
        """Successively remove all empty folders starting with `subpath` and
        proceeding "up" through directory tree until reaching the :attr:`root`
        folder.
        """
        # Don't attempt to remove any folders if subpath is not a
        # subdirectory of the root directory.
        if not self.haspath(subpath):
            return

        while subpath != self.root:
            if len(os.listdir(subpath)) > 0 or os.path.islink(subpath):
                break
            os.rmdir(subpath)
            subpath = os.path.dirname(subpath)

    def files(self):
        """Return generator that yields all files under :attr:`root` directory.
        """
        for folder, subfolders, files in os.walk(self.root):
            for file_ in files:
                yield os.path.abspath(os.path.join(folder, file_))

    def folders(self):
        """Return generator that yields all folders under :attr:`root`
        directory that directly contain files.
        """
        for folder, subfolders, files in os.walk(self.root):
            if files:
                yield folder

    def exists(self, id_or_path):
        """Check whether a given file id exsists on disk."""
        return bool(self.realpath(id_or_path))

    def haspath(self, path):
        """Return whether `path` is a subdirectory of the :attr:`root`
        directory.
        """
        return issubdir(path, self.root)

    def makepath(self, path):
        """Physically create the folder path on disk."""
        mkpath(path, mode=self.dmode)

    def copy(self, stream, id, extension=None):
        """Copy the contents of `stream` onto disk with an optional file
        extension appended. The copy process using a temporary file to store
        the initial contents and then moves this file to it's final location.
        """
        filepath = self.filepath(id, extension)

        if not os.path.isfile(filepath):
            with tmpfile(stream, self.fmode) as fname:
                self.makepath(os.path.dirname(filepath))
                shutil.copy(fname, filepath)

        return filepath

    def realpath(self, id_or_path):
        """Attempt to determine the real path of a file id or path through
        successive checking of candidate paths. If the real path is stored with
        an extension, the path is considered a match if the basename matches
        the expected file path of the id.
        """
        # Check for direct match.
        if os.path.isfile(id_or_path):
            return id_or_path

        # Check if tokenized id matches.
        filepath = self.filepath(id_or_path)
        if os.path.isfile(filepath):
            return filepath

        # Check if tokenized id with any extension matches.
        paths = glob.glob('{0}.*'.format(filepath))
        if paths:
            return paths[0]

        # Could not determine a match.
        return None

    def filepath(self, id, extension=''):
        """Build the file path for a given hash id. Optionally, append a
        file extension.
        """
        paths = self.tokenize(id)

        if extension and not extension.startswith(os.extsep):
            extension = os.extsep + extension
        elif not extension:
            extension = ''

        return os.path.join(self.root, *paths) + extension

    def computehash(self, stream):
        """Compute hash of file using :attr:`algorithm`."""
        hashobj = hashlib.new(self.algorithm)
        for data in stream:
            hashobj.update(to_bytes(data))
        return hashobj.hexdigest()

    def tokenize(self, id):
        """Convert content ID into tokens that will become the folder tree
        structure.
        """
        # This creates a list of `depth` number of tokens with length
        # `length` from the first part of the id plus the remainder.
        return compact([id[i * self.length:self.length * (i + 1)]
                        for i in range(self.depth)] +
                       [id[self.depth * self.length:]])

    def detokenize(self, path):
        """Return tokenized path's hash value."""
        if not self.haspath(path):
            raise ValueError(('Cannot detokenize path. The path "{0}" is not '
                              'a subdirectory of the root directory "{1}"'
                              .format(path, self.root)))

        path = os.path.realpath(path).split(self.root)[1]

        return os.path.splitext(path)[0].replace(os.sep, '')

    def repair(self, use_extension=True):
        """Repair any file locations whose content address doesn't match it's
        file path.
        """
        repaired = []
        corrupted = tuple(self.corrupted())
        oldmask = os.umask(0)

        try:
            for path, address in corrupted:
                if os.path.isfile(address.path):
                    # File already exists so just delete corrupted path.
                    os.remove(path)
                else:
                    # File doesn't exists so move it.
                    self.makepath(os.path.dirname(address.path))
                    shutil.move(path, address.path)

                os.chmod(address.path, self.fmode)
                repaired.append((path, address))
        finally:
            os.umask(oldmask)

        return repaired

    def corrupted(self, use_extension=True):
        """Return generator that yields corrupted files."""
        for path in self.files():
            stream = Stream(path)

            with closing(stream):
                id = self.computehash(stream)

            extension = os.path.splitext(path)[1] if use_extension else None
            expected_path = self.filepath(id, extension)

            if expected_path != path:
                yield (path, Address(id, expected_path))


class Address(namedtuple('Address', ['id', 'path'])):
    """File Address containing file's path on disk and it's content hash."""
    pass


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
