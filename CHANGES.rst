Changelog
=========


v0.2.0 (2015-05-29)
-------------------

- Rename ``HashFS.get`` to ``HashFS.open``. (**breaking change**)
- Add ``HashFS.get()`` method that returns a ``HashAddress`` or ``None`` given a file ID or path.


v0.1.0 (2015-05-28)
-------------------

- Add ``HashFS.get()`` method that retrieves a reader object given a file ID or path.
- Add ``HashFS.delete()`` method that deletes a file ID or path.
- Add ``HashFS.folders()`` method that returns the folder paths that directly contain files (i.e. subpaths that only contain folders are ignored).
- Add ``HashFS.detokenize()`` method that returns the file ID contained in a file path.
- Add ``HashFS.repair()`` method that reindexes any files under root directory whose file path doesn't not match its tokenized file ID.
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
