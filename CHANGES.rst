Changelog
=========


v0.1.0 (2015-05-28)
-------------------

- Add ``HashFS.get()`` method for retrieving a reader object given a file digest or path.
- Add ``HashFS.delete()`` method for deleting a file digest or path.
- Add ``HashFS.folders()`` method that returns the folder paths that directly contain files (i.e. subpaths that only contain folders are ignored).
- Add ``HashFS.detokenize()`` method that returns the file digest contained in a file path.
- Add ``HashFS.repair()`` method that reindexes any files under root directory whose file path doesn't not match its tokenized file digest.
- Rename ``Address`` classs to ``HashAddress``. (**breaking change**)
- Rename ``HashAddress.digest`` to ``HashAddress.id``. (**breaking change**)
- Rename ``HashAddress.path`` to ``HashAddress.abspath``. (**breaking change**)
- Add ``HashAddress.relpath`` which represents path relative to ``HashFS.root``.


v0.0.1 (2015-05-27)
-------------------

- First release.
- Add ``HashFS`` class.
- Add ``HashFS.put()`` method that saves a file path or file-like object by content hash.
- Add ``HashFS.files()`` method that returns all files under root directory.
- Add ``HashFS.exists()`` which checks either a file hash or file path for existence.
