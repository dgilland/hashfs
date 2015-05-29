******
HashFS
******

|version| |travis| |coveralls| |license|


HashFS is a content-addressable file management system. What does that mean? Simply, that HashFS manages a directory where files are saved based on the file's hash.

Typical use cases for this kind of system are ones where:

- Files are written once and never change (e.g. image storage).
- It's desirable to have no duplicate files (e.g. user uploads).
- File metadata is stored elsewhere (e.g. in a database).


Links
=====

- Project: https://github.com/dgilland/hashfs
- Documentation: http://hashfs.readthedocs.org
- PyPI: https://pypi.python.org/pypi/hashfs/
- TravisCI: https://travis-ci.org/dgilland/hashfs


Quickstart
==========

Install using pip:


::

    pip install hashfs


Initialization
--------------

.. code-block:: python

    from hashfs import HashFS


Designate a root folder for ``HashFS``. If the folder doesn't already exist, it will be created.


.. code-block:: python

    # Set the `depth` to the number of subfolders the file's hash should be split when saving.
    # Set the `length` to the desired length of each subfolder.
    fs = HashFS('temp_hashfs', depth=4, length=1, algorithm='sha256')

    # With depth=4 and length=1, files will be saved in the following pattern:
    # temp_hashfs/a/b/c/d/efghijklmnopqrstuvwxyz

    # With depth=3 and length=2, files will be saved in the following pattern:
    # temp_hashfs/ab/cd/ef/ghijklmnopqrstuvwxyz


**NOTE:** The ``algorithm`` value should be a valid string argument to ``hashlib.new()``.


Storing Content
---------------

Add content to the folder using either readable objects (e.g. ``StringIO``) or file paths (e.g. ``'a/path/to/some/file'``).


.. code-block:: python

    from io import StringIO

    some_content = StringIO('some content')

    address = fs.put(some_content)

    # Or if you'd like to save the file with an extension...
    address = fs.put(some_content, '.txt')

    # The id of the file (i.e. the hexdigest of its contents).
    address.id

    # The absolute path where the file was saved.
    address.abspath

    # The path relative to fs.root.
    address.relpath


Retrieving File Address
-----------------------

Get a file's ``HashAddress`` by address ID or path. This address would be identical to the address returned by ``put()``.

.. code-block:: python

    assert fs.get(address.id) == address
    assert fs.get(address.relpath) == address
    assert fs.get(address.abspath) == address
    assert fs.get('invalid') is None


Retrieving Content
------------------

Get a ``BufferedReader`` handler for an existing file by address ID or path.


.. code-block:: python

    fileio = fs.open(address.id)

    # Or using the full path...
    fileio = fs.open(address.abspath)

    # Or using a path relative to fs.root
    fileio = fs.open(address.relpath)


**NOTE:** When getting a file that was saved with an extension, it's not necessary to supply the extension. Extensions are ignored when looking for a file based on the ID or path.


Removing Content
----------------

Delete a file by address ID or path.


.. code-block:: python

    fs.delete(address.id)
    fs.delete(address.abspath)
    fs.delete(address.relpath)


**NOTE:** When a file is deleted, any parent directories above the file will also be deleted if they are empty directories.


Repairing Content
-----------------

The ``HashFS`` files may not always be in sync with it's ``depth``, ``length``, or ``algorithm`` settings (e.g. if ``HashFS`` takes ownership of a directory that wasn't previously stored using content hashes or if the ``HashFS`` settings change). These files can be easily reindexed using ``repair()``.


.. code-block:: python

    repaired = fs.repair()

    # Or if you want to drop file extensions...
    repaired = fs.repair(extensions=False)


**WARNING:** It's recommended that a backup of the directory be made before reparing just in case something goes wrong.


For more details, please see the full documentation at http://hashfs.readthedocs.org.



.. |version| image:: http://img.shields.io/pypi/v/hashfs.svg?style=flat-square
    :target: https://pypi.python.org/pypi/hashfs/

.. |travis| image:: http://img.shields.io/travis/dgilland/hashfs/master.svg?style=flat-square
    :target: https://travis-ci.org/dgilland/hashfs

.. |coveralls| image:: http://img.shields.io/coveralls/dgilland/hashfs/master.svg?style=flat-square
    :target: https://coveralls.io/r/dgilland/hashfs

.. |license| image:: http://img.shields.io/pypi/l/hashfs.svg?style=flat-square
    :target: https://pypi.python.org/pypi/hashfs/