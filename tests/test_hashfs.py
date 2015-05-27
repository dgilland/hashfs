# -*- coding: utf-8 -*-

from io import StringIO, BufferedReader
import os

import pytest

import hashfs


@pytest.fixture
def testpath(tmpdir):
    return tmpdir.mkdir('hashfs')


@pytest.fixture
def testfile(testpath):
    return testpath.join('hashfs.txt')


@pytest.fixture
def stringio():
    return StringIO(u'foo')


@pytest.yield_fixture
def fileio(testfile):
    with open(str(testfile), 'wb') as io:
        io.write(b'foo')

    io = open(str(testfile), 'rb')

    yield io

    io.close()


@pytest.fixture
def filepath(testfile):
    testfile.write(b'foo')
    return testfile


def assert_file_put(testpath, fs, address):
    path = address.path[len(fs.root):]
    directory = os.path.dirname(path)
    dir_parts = [part for part in directory.split(os.path.sep) if part]

    assert address.path in tuple(testpath.visit())
    assert fs.exists(address.digest)
    assert os.path.splitext(path.replace(os.path.sep, ''))[0] == address.digest
    assert len(dir_parts) == fs.depth
    assert all(len(part) == fs.length for part in dir_parts)


def test_hashfs_put_stringio(testpath, stringio):
    fs = hashfs.HashFS(str(testpath))
    address = fs.put(stringio)

    assert_file_put(testpath, fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == stringio.getvalue().encode('utf8')


def test_hashfs_put_fileobj(testpath, fileio):
    fs = hashfs.HashFS(str(testpath))
    address = fs.put(fileio)

    assert_file_put(testpath, fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == fileio.read()


def test_hashfs_put_file(testpath, filepath):
    fs = hashfs.HashFS(str(testpath))
    address = fs.put(str(filepath))

    assert_file_put(testpath, fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == filepath.read().encode('utf8')


@pytest.mark.parametrize('extension', [
    'txt',
    '.txt',
    'md',
    '.md'
])
def test_hashfs_put_extension(testpath, stringio, extension):
    fs = hashfs.HashFS(str(testpath))
    address = fs.put(stringio, extension)

    assert_file_put(testpath, fs, address)
    assert os.path.sep in address.path
    assert os.path.splitext(address.path)[1].endswith(extension)


def test_hashfs_put_invalid(testpath):
    fs = hashfs.HashFS(str(testpath))

    with pytest.raises(ValueError):
        fs.put('foo')


@pytest.mark.parametrize('extension,address_attr', [
    ('', 'digest'),
    ('.txt', 'digest'),
    ('txt', 'digest'),
    ('', 'path'),
    ('.txt', 'path'),
    ('txt', 'path'),
])
def test_hashfs_get(testpath, stringio, extension, address_attr):
    fs = hashfs.HashFS(str(testpath))
    address = fs.put(stringio, extension)

    fileobj = fs.get(getattr(address, address_attr))

    assert isinstance(fileobj, BufferedReader)
    assert fileobj.read() == stringio.getvalue()

    fileobj.close()


def test_hashfs_repair(testpath, testfile):
    testfile.write('qux')
    fs = hashfs.HashFS(str(testpath))

    assert os.path.isfile(str(testfile))

    repaired = fs.repair()
    original_path, address = repaired[0]

    assert original_path == str(testfile)
    assert not os.path.isfile(original_path)
    assert_file_put(testpath, fs, address)
