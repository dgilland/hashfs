"""Module for HashFS class.
"""

from collections import namedtuple
from contextlib import contextmanager, closing
import glob
import hashlib
import sys
import io
import os
import shutil
from tempfile import NamedTemporaryFile

from .utils import issubdir, shard
from ._compat import to_bytes, walk, FileExistsError


class HashFS(object):
    """Content addressable file manager.

    Attributes:
        root (str): Directory path used as root of storage space.
        depth (int, optional): Depth of subfolders to create when saving a
            file.
        width (int, optional): Width of each subfolder to create when saving a
            file.
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

    def __init__(
        self, root, depth=4, width=1, algorithm="sha256", fmode=0o664, dmode=0o755
    ):
        self.root = os.path.realpath(root)
        self.depth = depth
        self.width = width
        self.algorithm = algorithm
        self.fmode = fmode
        self.dmode = dmode

    def put(self, file, extension=None):
        """Store contents of `file` on disk using its content hash for the
        address.

        Args:
            file (mixed): Readable object or path to file.
            extension (str, optional): Optional extension to append to file
                when saving.

        Returns:
            HashAddress: File's hash address.
        """
        stream = Stream(file)

        with closing(stream):
            id = self.computehash(stream)
            filepath, is_duplicate = self._copy(stream, id, extension)

        return HashAddress(id, self.relpath(filepath), filepath, is_duplicate)

    def _copy(self, stream, id, extension=None):
        """Copy the contents of `stream` onto disk with an optional file
        extension appended. The copy process uses a temporary file to store the
        initial contents and then moves that file to it's final location.
        """
        filepath = self.idpath(id, extension)

        if not os.path.isfile(filepath):
            # Only move file if it doesn't already exist.
            is_duplicate = False
            fname = self._mktempfile(stream)
            self.makepath(os.path.dirname(filepath))
            shutil.move(fname, filepath)
        else:
            is_duplicate = True

        return (filepath, is_duplicate)

    def _mktempfile(self, stream):
        """Create a named temporary file from a :class:`Stream` object and
        return its filename.
        """
        tmp = NamedTemporaryFile(delete=False)

        if self.fmode is not None:
            oldmask = os.umask(0)

            try:
                os.chmod(tmp.name, self.fmode)
            finally:
                os.umask(oldmask)

        for data in stream:
            tmp.write(to_bytes(data))

        tmp.close()

        return tmp.name

    def get(self, file):
        """Return :class:`HashAdress` from given id or path. If `file` does not
        refer to a valid file, then ``None`` is returned.

        Args:
            file (str): Address ID or path of file.

        Returns:
            HashAddress: File's hash address.
        """
        realpath = self.realpath(file)

        if realpath is None:
            return None
        else:
            return HashAddress(self.unshard(realpath), self.relpath(realpath), realpath)

    def open(self, file, mode="rb"):
        """Return open buffer object from given id or path.

        Args:
            file (str): Address ID or path of file.
            mode (str, optional): Mode to open file in. Defaults to ``'rb'``.

        Returns:
            Buffer: An ``io`` buffer dependent on the `mode`.

        Raises:
            IOError: If file doesn't exist.
        """
        realpath = self.realpath(file)
        if realpath is None:
            raise IOError("Could not locate file: {0}".format(file))

        return io.open(realpath, mode)

    def delete(self, file):
        """Delete file using id or path. Remove any empty directories after
        deleting. No exception is raised if file doesn't exist.

        Args:
            file (str): Address ID or path of file.
        """
        realpath = self.realpath(file)
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
        """Return generator that yields all files in the :attr:`root`
        directory.
        """
        for folder, subfolders, files in walk(self.root):
            for file in files:
                yield os.path.abspath(os.path.join(folder, file))

    def folders(self):
        """Return generator that yields all folders in the :attr:`root`
        directory that contain files.
        """
        for folder, subfolders, files in walk(self.root):
            if files:
                yield folder

    def count(self):
        """Return count of the number of files in the :attr:`root` directory.
        """
        count = 0
        for _ in self:
            count += 1
        return count

    def size(self):
        """Return the total size in bytes of all files in the :attr:`root`
        directory.
        """
        total = 0

        for path in self.files():
            total += os.path.getsize(path)

        return total

    def exists(self, file):
        """Check whether a given file id or path exists on disk."""
        return bool(self.realpath(file))

    def haspath(self, path):
        """Return whether `path` is a subdirectory of the :attr:`root`
        directory.
        """
        return issubdir(path, self.root)

    def makepath(self, path):
        """Physically create the folder path on disk."""
        try:
            os.makedirs(path, self.dmode)
        except FileExistsError:
            assert os.path.isdir(path), "expected {} to be a directory".format(path)

    def relpath(self, path):
        """Return `path` relative to the :attr:`root` directory."""
        return os.path.relpath(path, self.root)

    def realpath(self, file):
        """Attempt to determine the real path of a file id or path through
        successive checking of candidate paths. If the real path is stored with
        an extension, the path is considered a match if the basename matches
        the expected file path of the id.
        """
        # Check for absoluate path.
        if os.path.isfile(file):
            return file

        # Check for relative path.
        relpath = os.path.join(self.root, file)
        if os.path.isfile(relpath):
            return relpath

        # Check for sharded path.
        filepath = self.idpath(file)
        if os.path.isfile(filepath):
            return filepath

        # Check for sharded path with any extension.
        paths = glob.glob("{0}.*".format(filepath))
        if paths:
            return paths[0]

        # Could not determine a match.
        return None

    def idpath(self, id, extension=""):
        """Build the file path for a given hash id. Optionally, append a
        file extension.
        """
        paths = self.shard(id)

        if extension and not extension.startswith(os.extsep):
            extension = os.extsep + extension
        elif not extension:
            extension = ""

        return os.path.join(self.root, *paths) + extension

    def computehash(self, stream):
        """Compute hash of file using :attr:`algorithm`."""
        hashobj = hashlib.new(self.algorithm)
        for data in stream:
            hashobj.update(to_bytes(data))
        return hashobj.hexdigest()

    def shard(self, id):
        """Shard content ID into subfolders."""
        return shard(id, self.depth, self.width)

    def unshard(self, path):
        """Unshard path to determine hash value."""
        if not self.haspath(path):
            raise ValueError(
                "Cannot unshard path. The path {0!r} is not "
                "a subdirectory of the root directory {1!r}".format(path, self.root)
            )

        return os.path.splitext(self.relpath(path))[0].replace(os.sep, "")

    def repair(self, extensions=True):
        """Repair any file locations whose content address doesn't match it's
        file path.
        """
        repaired = []
        corrupted = tuple(self.corrupted(extensions=extensions))
        oldmask = os.umask(0)

        try:
            for path, address in corrupted:
                if os.path.isfile(address.abspath):
                    # File already exists so just delete corrupted path.
                    os.remove(path)
                else:
                    # File doesn't exists so move it.
                    self.makepath(os.path.dirname(address.abspath))
                    shutil.move(path, address.abspath)

                os.chmod(address.abspath, self.fmode)
                repaired.append((path, address))
        finally:
            os.umask(oldmask)

        return repaired

    def corrupted(self, extensions=True):
        """Return generator that yields corrupted files as ``(path, address)``
        where ``path`` is the path of the corrupted file and ``address`` is
        the :class:`HashAddress` of the expected location.
        """
        for path in self.files():
            stream = Stream(path)

            with closing(stream):
                id = self.computehash(stream)

            extension = os.path.splitext(path)[1] if extensions else None
            expected_path = self.idpath(id, extension)

            if expected_path != path:
                yield (
                    path,
                    HashAddress(id, self.relpath(expected_path), expected_path),
                )

    def __contains__(self, file):
        """Return whether a given file id or path is contained in the
        :attr:`root` directory.
        """
        return self.exists(file)

    def __iter__(self):
        """Iterate over all files in the :attr:`root` directory."""
        return self.files()

    def __len__(self):
        """Return count of the number of files in the :attr:`root` directory.
        """
        return self.count()


class HashAddress(
    namedtuple("HashAddress", ["id", "relpath", "abspath", "is_duplicate"])
):
    """File address containing file's path on disk and it's content hash ID.

    Attributes:
        id (str): Hash ID (hexdigest) of file contents.
        relpath (str): Relative path location to :attr:`HashFS.root`.
        abspath (str): Absoluate path location of file on disk.
        is_duplicate (boolean, optional): Whether the hash address created was
            a duplicate of a previously existing file. Can only be ``True``
            after a put operation. Defaults to ``False``.
    """

    def __new__(cls, id, relpath, abspath, is_duplicate=False):
        return super(HashAddress, cls).__new__(cls, id, relpath, abspath, is_duplicate)


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
        if hasattr(obj, "read"):
            pos = obj.tell()
        elif os.path.isfile(obj):
            obj = io.open(obj, "rb")
            pos = None
        else:
            raise ValueError("Object must be a valid file path or a readable object")

        try:
            file_stat = os.stat(obj.name)
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
