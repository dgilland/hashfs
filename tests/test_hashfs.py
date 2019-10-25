# -*- coding: utf-8 -*-

from io import StringIO, BufferedReader
import os
import string

import py
import pytest

import hashfs
from hashfs._compat import to_bytes


@pytest.fixture
def testpath(tmpdir):
    return tmpdir.mkdir("hashfs")


@pytest.fixture
def testfile(testpath):
    return testpath.join("hashfs.txt")


@pytest.fixture
def stringio():
    return StringIO(u"foo")


@pytest.yield_fixture
def fileio(testfile):
    with open(str(testfile), "wb") as io:
        io.write(b"foo")

    io = open(str(testfile), "rb")

    yield io

    io.close()


@pytest.fixture
def filepath(testfile):
    testfile.write(b"foo")
    return testfile


@pytest.fixture
def fs(testpath):
    return hashfs.HashFS(str(testpath))


def put_range(fs, count):
    return dict(
        (address.abspath, address)
        for address in (fs.put(StringIO(u"{0}".format(i))) for i in range(count))
    )


def assert_file_put(fs, address):
    directory = os.path.dirname(address.relpath)
    dir_parts = [part for part in directory.split(os.path.sep) if part]

    assert address.abspath in tuple(py.path.local(fs.root).visit())
    assert fs.exists(address.id)

    id = os.path.splitext(address.relpath.replace(os.path.sep, ""))[0]
    assert id == address.id

    assert len(dir_parts) == fs.depth
    assert all(len(part) == fs.width for part in dir_parts)


def test_hashfs_put_stringio(fs, stringio):
    address = fs.put(stringio)

    assert_file_put(fs, address)

    with open(address.abspath, "rb") as fileobj:
        assert fileobj.read() == to_bytes(stringio.getvalue())


def test_hashfs_put_fileobj(fs, fileio):
    address = fs.put(fileio)

    assert_file_put(fs, address)

    with open(address.abspath, "rb") as fileobj:
        assert fileobj.read() == fileio.read()


def test_hashfs_put_file(fs, filepath):
    address = fs.put(str(filepath))

    assert_file_put(fs, address)

    with open(address.abspath, "rb") as fileobj:
        assert fileobj.read() == to_bytes(filepath.read())


def test_hashfs_put_duplicate(fs, stringio):
    address_a = fs.put(stringio)
    address_b = fs.put(stringio)

    assert not address_a.is_duplicate
    assert address_b.is_duplicate


@pytest.mark.parametrize("extension", ["txt", ".txt", "md", ".md"])
def test_hashfs_put_extension(fs, stringio, extension):
    address = fs.put(stringio, extension)

    assert_file_put(fs, address)
    assert os.path.sep in address.abspath
    assert os.path.splitext(address.abspath)[1].endswith(extension)
    assert not address.is_duplicate


def test_hashfs_put_error(fs):
    with pytest.raises(ValueError):
        fs.put("foo")


def test_hashfs_address(fs, stringio):
    address = fs.put(stringio)

    assert fs.root not in address.relpath
    assert os.path.join(fs.root, address.relpath) == address.abspath
    assert address.relpath.replace(os.sep, "") == address.id
    assert not address.is_duplicate


@pytest.mark.parametrize(
    "extension,address_attr",
    [
        ("", "id"),
        (".txt", "id"),
        ("txt", "id"),
        ("", "abspath"),
        (".txt", "abspath"),
        ("txt", "abspath"),
    ],
)
def test_hashfs_open(fs, stringio, extension, address_attr):
    address = fs.put(stringio, extension)

    fileobj = fs.open(getattr(address, address_attr))

    assert isinstance(fileobj, BufferedReader)
    assert fileobj.read() == to_bytes(stringio.getvalue())

    fileobj.close()


def test_hashfs_open_error(fs):
    with pytest.raises(IOError):
        fs.open("invalid")


def test_hashfs_exists(fs, stringio):
    address = fs.put(stringio)

    assert fs.exists(address.id)
    assert fs.exists(address.relpath)
    assert fs.exists(address.abspath)


def test_hashfs_contains(fs, stringio):
    address = fs.put(stringio)

    assert address.id in fs
    assert address.relpath in fs
    assert address.abspath in fs


def test_hashfs_get(fs, stringio):
    address = fs.put(stringio)

    assert not address.is_duplicate
    assert fs.get(address.id) == address
    assert fs.get(address.relpath) == address
    assert fs.get(address.abspath) == address
    assert fs.get("invalid") is None


@pytest.mark.parametrize("address_attr", ["id", "abspath"])
def test_hashfs_delete(fs, stringio, address_attr):
    address = fs.put(stringio)

    fs.delete(getattr(address, address_attr))
    assert len(os.listdir(fs.root)) == 0


def test_hashfs_delete_error(fs):
    fs.delete("invalid")


def test_hashfs_remove_empty(fs):
    subpath1 = os.path.join(fs.root, "1", "2", "3")
    subpath2 = os.path.join(fs.root, "1", "4", "5")
    subpath3 = os.path.join(fs.root, "6", "7", "8")

    fs.makepath(subpath1)
    fs.makepath(subpath2)
    fs.makepath(subpath3)

    assert os.path.exists(subpath1)
    assert os.path.exists(subpath2)
    assert os.path.exists(subpath3)

    fs.remove_empty(subpath1)
    fs.remove_empty(subpath3)

    assert not os.path.exists(subpath1)
    assert os.path.exists(subpath2)
    assert not os.path.exists(subpath3)


def test_hashfs_remove_empty_subdir(fs):
    fs.remove_empty(fs.root)

    assert os.path.exists(fs.root)

    fs.remove_empty(os.path.realpath(os.path.join(fs.root, "..")))

    assert os.path.exists(fs.root)


def test_hashfs_unshard(fs, stringio):
    address = fs.put(stringio)
    assert fs.unshard(address.abspath) == address.id


def test_hashfs_unshard_error(fs):
    with pytest.raises(ValueError):
        fs.unshard("invalid")


def test_hashfs_repair(fs, stringio):
    original_address = fs.put(stringio)
    newfs = hashfs.HashFS(fs.root, depth=1)

    repaired = newfs.repair()

    assert len(repaired) == 1
    original_path, address = repaired[0]

    assert original_path == original_address.abspath
    assert not os.path.isfile(original_path)
    assert_file_put(newfs, address)


def test_hashfs_repair_duplicates(fs, stringio):
    original_address = fs.put(stringio)
    newfs = hashfs.HashFS(fs.root, depth=1)
    newfs.put(stringio)

    repaired = newfs.repair()

    assert len(repaired) == 1
    original_path, address = repaired[0]

    assert original_path == original_address.abspath
    assert not os.path.isfile(original_path)
    assert_file_put(newfs, address)


def test_hashfs_files(fs):
    count = 5
    addresses = put_range(fs, count)
    files = list(fs.files())

    assert len(files) == count

    for file in files:
        assert os.path.isfile(file)
        assert file in addresses
        assert addresses[file].abspath == file
        assert addresses[file].id == fs.unshard(file)


def test_hashfs_iter(fs):
    count = 5
    addresses = put_range(fs, count)
    test_count = 0

    for file in fs:
        test_count += 1
        assert os.path.isfile(file)
        assert file in addresses
        assert addresses[file].abspath == file
        assert addresses[file].id == fs.unshard(file)

    assert test_count == count


def test_hashfs_count(fs):
    count = 5
    put_range(fs, count)
    assert fs.count() == count


def test_hashfs_len(fs):
    count = 5
    put_range(fs, count)
    assert len(fs) == count


def test_hashfs_folders(fs):
    count = 5
    put_range(fs, count)
    folders = list(fs.folders())

    assert len(folders) == count

    for folder in folders:
        assert os.path.exists(folder)
        assert os.path.isfile(os.path.join(folder, os.listdir(folder)[0]))


def test_hashfs_size(fs):
    fs.put(StringIO(u"{0}".format(string.ascii_lowercase)))
    fs.put(StringIO(u"{0}".format(string.ascii_uppercase)))
    expected = len(string.ascii_lowercase) + len(string.ascii_uppercase)

    assert fs.size() == expected
