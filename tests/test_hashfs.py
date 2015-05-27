# -*- coding: utf-8 -*-

from io import StringIO, BufferedReader
import os

import py
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


@pytest.fixture
def fs(testpath):
    return hashfs.HashFS(str(testpath))


def assert_file_put(fs, address):
    path = address.path[len(fs.root):]
    directory = os.path.dirname(path)
    dir_parts = [part for part in directory.split(os.path.sep) if part]

    assert address.path in tuple(py.path.local(fs.root).visit())
    assert fs.exists(address.digest)
    assert os.path.splitext(path.replace(os.path.sep, ''))[0] == address.digest
    assert len(dir_parts) == fs.depth
    assert all(len(part) == fs.length for part in dir_parts)


def test_hashfs_put_stringio(fs, stringio):
    address = fs.put(stringio)

    assert_file_put(fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == stringio.getvalue().encode('utf8')


def test_hashfs_put_fileobj(fs, fileio):
    address = fs.put(fileio)

    assert_file_put(fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == fileio.read()


def test_hashfs_put_file(fs, filepath):
    address = fs.put(str(filepath))

    assert_file_put(fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == filepath.read().encode('utf8')


@pytest.mark.parametrize('extension', [
    'txt',
    '.txt',
    'md',
    '.md'
])
def test_hashfs_put_extension(fs, stringio, extension):
    address = fs.put(stringio, extension)

    assert_file_put(fs, address)
    assert os.path.sep in address.path
    assert os.path.splitext(address.path)[1].endswith(extension)


def test_hashfs_put_invalid(fs):
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
def test_hashfs_get(fs, stringio, extension, address_attr):
    address = fs.put(stringio, extension)

    fileobj = fs.get(getattr(address, address_attr))

    assert isinstance(fileobj, BufferedReader)
    assert fileobj.read() == stringio.getvalue()

    fileobj.close()


def test_hashfs_get_invalid(fs):
    with pytest.raises(IOError):
        fs.get('invalid')


@pytest.mark.parametrize('address_attr', [
   'digest',
   'path',
])
def test_hashfs_delete(fs, stringio, address_attr):
    address = fs.put(stringio)

    fs.delete(getattr(address, address_attr))
    assert len(os.listdir(fs.root)) == 0


def test_hashfs_delete_invalid(fs):
    fs.delete('invalid')


def test_hashfs_remove_empty(fs):
    subpath1 = os.path.join(fs.root, '1', '2', '3')
    subpath2 = os.path.join(fs.root, '1', '4', '5')
    subpath3 = os.path.join(fs.root, '6', '7', '8')

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

    fs.remove_empty(os.path.realpath(os.path.join(fs.root, '..')))

    assert os.path.exists(fs.root)


def test_hashfs_repair(fs, testfile):
    testfile.write('qux')

    assert os.path.isfile(str(testfile))

    repaired = fs.repair()
    original_path, address = repaired[0]

    assert original_path == str(testfile)
    assert not os.path.isfile(original_path)
    assert_file_put(fs, address)
