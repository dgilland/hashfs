"""Module for HashFS class."""

import hashlib
import io
import os
from contextlib import closing
from typing import Iterable, Optional, Tuple, Union

import fs as pyfs
import hashfs.utils as u
from fs.permissions import Permissions

Key = Union[str, u.HashAddress]


class HashFS(object):
    """Content addressable file manager. This is the Blueshift rewrite of
  https://github.com/dgilland/hashfs, using
  https://github.com/PyFilesystem/pyfilesystem2.

    Attributes:
        root: Directory path used as root of storage space.
        depth (int, optional): Depth of subfolders to create when saving a
            file.
        width (int, optional): Width of each subfolder to create when saving a
            file.
        algorithm (str): Hash algorithm to use when computing file hash.
            Algorithm should be available in ``hashlib`` module, ie, a member
            of `hashlib.algorithms_available`. Defaults to ``'sha256'``.
        dmode (int, optional): Directory mode permission to set for
            subdirectories. Defaults to ``0o755`` which allows owner/group to
            read/write and everyone else to read and everyone to execute.

  """

    def __init__(self,
                 root: Union[pyfs.base.FS, str],
                 depth: Optional[int] = 4,
                 width: Optional[int] = 1,
                 algorithm: hashlib.algorithms_available = "sha256",
                 dmode: Optional[int] = 0o755):

        self.fs = u.load_fs(root)
        self.depth = depth
        self.width = width
        self.algorithm = algorithm
        self.dmode = dmode

    def put(self, content, extension: Optional[str] = None) -> u.HashAddress:
        """Store contents of `content` in the backing filesystem using its content hash
    for the address.

    Args:
      content: Readable object or path to file.
      extension: Optional extension to append to file when saving.

    Returns:
      File's hash address.

    """
        with closing(u.Stream(content, fs=self.fs)) as stream:
            hashid = self._computehash(stream)
            path, is_duplicate = self._copy(stream, hashid, extension)

        return u.HashAddress(hashid, path, is_duplicate)

    def get(self, k: Key) -> Optional[u.HashAddress]:
        """Return :class:`HashAddress` from given id or path. If `k` does not refer to
       a valid file, then `None` is returned.

    Args:
      k: Address ID or path of file.

    Returns:
      File's hash address.

    """
        path = self._fs_path(k)

        if path is None:
            return None

        return u.HashAddress(self._unshard(path), path)

    def open(self, k: Key, mode: str = "rb") -> io.IOBase:
        """Return open IOBase object from given id or path.

        Args:
            k: Address ID or path of file.
            mode (str, optional): Mode to open file in. Defaults to ``'rb'``.

        Returns:
            Buffer: An ``io`` buffer dependent on the `mode`.

        Raises:
            IOError: If file doesn't exist.

    """
        path = self._fs_path(k)
        if path is None:
            raise IOError("Could not locate file: {0}".format(k))

        return self.fs.open(path, mode)

    def delete(self, k: Key) -> None:
        """Delete file using id or path. Remove any empty directories after
        deleting. No exception is raised if file doesn't exist.

        Args:
            file (str): Address ID or path of file.
        """
        path = self._fs_path(k)
        if path is None:
            return

        try:
            self.fs.remove(path)
        except OSError:  # pragma: no cover
            # Attempting to delete a directory.
            pass
        else:
            self._remove_empty(pyfs.path.dirname(path))

    def files(self) -> Iterable[str]:
        """Return generator that yields all files in the :attr:`fs`.

    """
        return self.fs.walk.files()

    def folders(self) -> Iterable[str]:
        """Return generator that yields all directories in the :attr:`fs` that contain
        files.

    """
        for step in self.fs.walk():
            if step.files:
                yield step.path

    def count(self) -> int:
        """Return count of the number of files in the backing :attr:`fs`.
        """
        return sum(1 for _, info in self.fs.walk.info() if not info.is_file)

    def size(self) -> int:
        """Return the total size in bytes of all files in the :attr:`root`
        directory.
        """
        return sum(info.size
                   for _, info in self.fs.walk.info(namespaces=['details'])
                   if not info.is_dir)

    def exists(self, k: Key) -> bool:
        """Check whether a given file id or path exists on disk."""
        return bool(self._fs_path(k))

    def repair(self, extensions: bool = True) -> Iterable[str]:
        """Repair any file locations whose content address doesn't match it's
        file path.
        """
        repaired = []
        corrupted = self._corrupted(extensions=extensions)

        for path, address in corrupted:
            if self.fs.isfile(path):
                # File already exists so just delete corrupted path.
                self.fs.remove(path)

            else:
                # File doesn't exist, so move it.
                self._makedirs(pyfs.path.dirname(path))
                self.fs.move(path, address.relpath)

            repaired.append((path, address))

        # check for empty directories created by the repair.
        for d in {pyfs.path.dirname(p) for p, _ in repaired}:
            self._remove_empty(d)

        return repaired

    def __contains__(self, k: Key) -> bool:
        """Return whether a given file id or path is contained in the
        :attr:`root` directory.
        """
        return self.exists(k)

    def __iter__(self) -> Iterable[str]:
        """Iterate over all files in the backing store."""
        return self.files()

    def __len__(self) -> int:
        """Return count of the number of files tracked by the backing filesystem.

    """
        return self.count()

    def _computehash(self, stream: u.Stream) -> str:
        """Compute hash of file using :attr:`algorithm`."""
        return u.computehash(stream, self.algorithm)

    def _copy(self,
              stream: u.Stream,
              hashid: str,
              extension: Optional[str] = None):
        """Copy the contents of `stream` onto disk with an optional file extension
        appended.

        Returns a pair of

        - relative path,
        - boolean noting whether or not we have a duplicate.

        """
        path = self._hashid_to_path(hashid, extension)

        if self.fs.isfile(path):
            is_duplicate = True

        else:
            # Only move file if it doesn't already exist.
            is_duplicate = False
            self._makedirs(pyfs.path.dirname(path))
            with closing(self.fs.open(path, mode='wb')) as p:
                for data in stream:
                    p.write(u.to_bytes(data))

        return (path, is_duplicate)

    def _remove_empty(self, path: str) -> None:
        """Successively remove all empty folders starting with `subpath` and
        proceeding "up" through directory tree until reaching the :attr:`root`
        folder.
        """
        try:
            pyfs.tools.remove_empty(self.fs, path)
        except pyfs.errors.ResourceNotFound:
            # Guard against paths that don't exist in the FS.
            return None

    def _makedirs(self, dir_path):
        """Physically create the folder path on disk."""

        try:
            # this is creating a directory, so we use dmode here.
            perms = Permissions.create(self.dmode)
            self.fs.makedirs(dir_path, permissions=perms, recreate=True)

        except pyfs.errors.DirectoryExpected:
            assert self.fs.isdir(
                dir_path), f"expected {dir_path} to be a directory"

    def _fs_path(self, k: Union[str, u.HashAddress]) -> Optional[str]:
        """Attempt to determine the real path of a file id or path through successive
    checking of candidate paths. If the real path is stored with an extension,
    the path is considered a match if the basename matches 'the expected file
    path of the id.

    """
        # if the input is ALREADY a hash address, pull out the relative path.
        if isinstance(k, u.HashAddress):
            k = k.relpath

        # Check if input was a fs path already.
        if self.fs.isfile(k):
            return k

        # Check if input was an ID.
        filepath = self._hashid_to_path(k)
        if self.fs.isfile(filepath):
            return filepath

        # Check the generated filepath to see if any version of the path exist with
        # some extension; return that if it exists..
        paths = self.fs.glob("{0}.*".format(filepath))
        if paths.count().files > 0:
            return next(iter(paths)).path

        # Could not determine a match.
        return None

    def _hashid_to_path(self, hashid: str, extension: str = "") -> str:
        """Build the relative file path for a given hash id. Optionally, append a file
    extension.

    """
        paths = self._shard(hashid)

        if extension and not extension.startswith(os.extsep):
            extension = os.extsep + extension
        elif not extension:
            extension = ""

        return pyfs.path.join(*paths) + extension

    def _shard(self, hashid: str) -> str:
        """Shard content ID into subfolders."""
        return u.shard(hashid, self.depth, self.width)

    def _unshard(self, path: str) -> str:
        """Unshard path to determine hash value."""
        if not self.fs.isfile(path):
            raise ValueError("Cannot unshard path. The path {0!r} doesn't exist"
                             "in the filesystem. {1!r}")

        return pyfs.path.splitext(path)[0].replace(os.sep, "")

    def _corrupted(self, extensions: bool = True
                  ) -> Iterable[Tuple[str, u.HashAddress]]:
        """Return generator that yields corrupted files as ``(path, address)``, where
    ``path`` is the path of the corrupted file and ``address`` is the
    :class:`HashAddress` of the expected location.

    """
        for path in self.files():
            with closing(u.Stream(path, fs=self.fs)) as stream:
                hashid = self._computehash(stream)

            extension = pyfs.path.splitext(path)[1] if extensions else None
            expected_path = self._hashid_to_path(hashid, extension)

            if pyfs.path.abspath(expected_path) != pyfs.path.abspath(path):
                yield (
                    path,
                    u.HashAddress(hashid, expected_path),
                )
