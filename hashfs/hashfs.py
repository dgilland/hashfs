"""Module for HashFS class.
"""

from collections import namedtuple
from contextlib import contextmanager, closing
from distutils.dir_util import mkpath
import glob
import hashlib
import io
import os
import errno
import shutil
from tempfile import NamedTemporaryFile

from .utils import issubdir, shard
from ._compat import to_bytes, walk, is_callable, list_dir_files


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
        put_strategy (mixed, optional): Default ``put_strategy`` for
            :meth:`put` method. See :meth:`put` for more information. Defaults
            to :attr:`PutStrategies.copy`.
        lowercase_extensions (bool, optional): Normalize all file extensions
            to lower case when adding files. Defaults to ``False``.
    """
    def __init__(self,
                 root,
                 depth=4,
                 width=1,
                 algorithm='sha256',
                 fmode=0o664,
                 dmode=0o755,
                 put_strategy=None,
                 lowercase_extensions=False):
        self.root = os.path.realpath(root)
        self.depth = depth
        self.width = width
        self.algorithm = algorithm
        self.fmode = fmode
        self.dmode = dmode
        self.put_strategy = (PutStrategies.get(put_strategy) or
                             PutStrategies.copy)
        self.lowercase_extensions = lowercase_extensions

    def put(self, file, extension=None, put_strategy=None, simulate=False):
        """Store contents of `file` on disk using its content hash for the
        address.

        Args:
            file (mixed): Readable object or path to file.
            extension (str, optional): Optional extension to append to file
                when saving.
            put_strategy (mixed, optional): The strategy to use for adding
                files; may be a function or the string name of one of the
                built-in put strategies declared in :class:`PutStrategies`
                class. Defaults to :attr:`PutStrategies.copy`.
            simulate (bool, optional): Return the :class:`HashAddress` of the
                file that would be appended but don't do anything.

        Put strategies are functions ``(hashfs, stream, filepath)`` where
        ``hashfs`` is the :class:`HashFS` instance from which :meth:`put` was
        called; ``stream`` is the :class:`Stream` object representing the
        data to add; and ``filepath`` is the string absolute file path inside
        the HashFS where it needs to be saved. The put strategy function should
        create the path ``filepath`` containing the data in ``stream``.

        There are currently two built-in put strategies: "copy" (the default)
        and "link". "link" attempts to hard link the file into the HashFS if
        the platform and underlying filesystem support it, and falls back to
        "copy" behaviour.

        Returns:
            HashAddress: File's hash address.
        """
        stream = Stream(file)

        if extension and self.lowercase_extensions:
            extension = extension.lower()

        with closing(stream):
            id = self.computehash(stream)
            filepath = self.idpath(id, extension)

            # Only move file if it doesn't already exist.
            if not os.path.isfile(filepath):
                is_duplicate = False
                if not simulate:
                    self.makepath(os.path.dirname(filepath))
                    put_strategy = (PutStrategies.get(put_strategy) or
                                    self.put_strategy or
                                    PutStrategies.copy)
                    put_strategy(self, stream, filepath)
            else:
                is_duplicate = True

        return HashAddress(id, self.relpath(filepath), filepath, is_duplicate)

    def putdir(self, root, extensions=True, recursive=False, **kwargs):
        """Put all files from a directory.

        Args:
            root (str): Path to the directory to add.
            extensions (bool, optional): Whether to add extensions when
                saving (extension will be taken from input file). Defaults to
                ``True``.
            recursive (bool, optional): Find files recursively in ``root``.
                Defaults to ``False``.
            put_strategy (mixed, optional): same as :meth:`put`.
            simulate (boo, optional): same as :meth:`put`.

        Yields :class:`HashAddress`es for all added files.
        """
        for file in find_files(root, recursive=recursive):
            extension = os.path.splitext(file)[1] if extensions else None
            address = self.put(file, extension=extension, **kwargs)
            yield (file, address)

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
            return HashAddress(self.unshard(realpath),
                               self.relpath(realpath),
                               realpath)

    def open(self, file, mode='rb'):
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
            raise IOError('Could not locate file: {0}'.format(file))

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
        for file in find_files(self.root, recursive=True):
            yield os.path.abspath(file)

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
        mkpath(path, mode=self.dmode)

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
        paths = glob.glob('{0}.*'.format(filepath))
        if paths:
            return paths[0]

        # Could not determine a match.
        return None

    def idpath(self, id, extension=''):
        """Build the file path for a given hash id. Optionally, append a
        file extension.
        """
        paths = self.shard(id)

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

    def shard(self, id):
        """Shard content ID into subfolders."""
        return shard(id, self.depth, self.width)

    def unshard(self, path):
        """Unshard path to determine hash value."""
        if not self.haspath(path):
            raise ValueError(('Cannot unshard path. The path "{0}" is not '
                              'a subdirectory of the root directory "{1}"'
                              .format(path, self.root)))

        return os.path.splitext(self.relpath(path))[0].replace(os.sep, '')

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
                yield (path, HashAddress(id,
                                         self.relpath(expected_path),
                                         expected_path))

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


def find_files(path, recursive=False):
    if recursive:
        for folder, subfolders, files in walk(path):
            for file in files:
                yield os.path.join(folder, file)
    else:
        for file in list_dir_files(path):
            yield file


class HashAddress(namedtuple('HashAddress',
                             ['id', 'relpath', 'abspath', 'is_duplicate'])):
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
        return super(HashAddress, cls).__new__(cls,
                                               id,
                                               relpath,
                                               abspath,
                                               is_duplicate)


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

        try:
            # Expose the original file path if available.
            # This allows put strategies to use OS functions, working with
            # paths, instead of being limited to the API provided by Python
            # file-like objects
            # name property can also hold int fd, so we make it None in that
            # case
            self.name = None if isinstance(obj.name, int) else obj.name
        except AttributeError:
            self.name = None

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


class PutStrategies:
    """Namespace for built-in put strategies.

    Should not be instantiated. Use the :meth:`get` static method to look up a
    strategy by name, or directly reference one of the included class methods.
    """

    @classmethod
    def get(cls, method):
        """Look up a stragegy by name string. You can also pass a function
        which will be returned as is."""
        if method:
            if method == 'get':
                raise ValueError("invalid put strategy name, 'get'")
            return method if is_callable(method) else getattr(cls, method)

    @staticmethod
    def copy(hashfs, src_stream, dst_path):
        """The default copy put strategy, writes the file object to a
        temporary file on disk and then moves it into place."""
        shutil.move(hashfs._mktempfile(src_stream), dst_path)

    if hasattr(os, 'link'):
        @classmethod
        def link(cls, hashfs, src_stream, dst_path):
            """Use os.link if available to create a hard link to the original
            file if the HashFS and the original file reside on the same
            filesystem and the filesystem supports hard links."""
            # Get the original file path exposed by the Stream instance
            src_path = src_stream.name
            # No path available because e.g. a StringIO was used
            if not src_path:
                # Just copy
                return cls.copy(hashfs, src_stream, dst_path)

            try:
                # Try to create the hard link
                os.link(src_path, dst_path)
            except EnvironmentError as e:
                # These are link specific errors. If any of these 3 are raised
                # we try to copy instead
                # EMLINK - src already has the maximum number of links to it
                # EXDEV - invalid cross-device link
                # EPERM - the dst filesystem does not support hard links
                # (note EPERM could also be another permissions error; these
                # will be raised again when we try to copy)
                if e.errno not in (errno.EMLINK, errno.EXDEV, errno.EPERM):
                    raise
                return cls.copy(hashfs, src_stream, dst_path)
            else:
                # After creating the hard link, make sure it has the correct
                # file permissions
                os.chmod(dst_path, hashfs.fmode)
    else:
        # Platform does not support os.link, so use the default copy strategy
        # instead
        link = copy
