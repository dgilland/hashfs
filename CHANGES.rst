Changelog
=========


v0.7.2 (2019-10-24)
-------------------

- Fix out-of-memory issue when computing file ID hashes of large files.


v0.7.1 (2018-10-13)
-------------------

- Replace usage of ``distutils.dir_util.mkpath`` with ``os.path.makedirs``.


v0.7.0 (2016-04-19)
-------------------

- Use ``shutil.move`` instead of ``shutil.copy`` to move temporary file created during ``put`` operation to ``HashFS`` directory.


v0.6.0 (2015-10-19)
-------------------

- Add faster ``scandir`` package for iterating over files/folders when platform is Python < 3.5. Scandir implementation was added to ``os`` module starting with Python 3.5.


v0.5.0 (2015-07-02)
-------------------

- Rename private method ``HashFS.copy`` to ``HashFS._copy``.
- Add ``is_duplicate`` attribute to ``HashAddress``.
- Make ``HashFS.put()`` return ``HashAddress`` with ``is_duplicate=True`` when file with same hash already exists on disk.


v0.4.0 (2015-06-03)
-------------------

- Add ``HashFS.size()`` method that returns the size of all files in bytes.
- Add ``HashFS.count()``/``HashFS.__len__()`` methods that return the count of all files.
- Add ``HashFS.__iter__()`` method to support iteration. Proxies to ``HashFS.files()``.
- Add ``HashFS.__contains__()`` method to support ``in`` operator. Proxies to ``HashFS.exists()``.
- Don't create the root directory (if it doesn't exist) until at least one file has been added.
- Fix ``HashFS.repair()`` not using ``extensions`` argument properly.


v0.3.0 (2015-06-02)
-------------------

- Rename ``HashFS.length`` parameter/property to ``width``. (**breaking change**)


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
