# -*- coding: utf-8 -*-

from io import StringIO
import os

import pytest

import shed


@pytest.fixture
def testpath(tmpdir):
    return tmpdir.mkdir('shed')


@pytest.fixture
def testfile(testpath):
    return testpath.join('shed.txt')


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


def test_shed_put_stringio(testpath, stringio):
    fs = shed.Shed(str(testpath))
    address = fs.put(stringio)

    assert_file_put(testpath, fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == stringio.getvalue().encode('utf8')


def test_shed_put_fileobj(testpath, fileio):
    fs = shed.Shed(str(testpath))
    address = fs.put(fileio)

    assert_file_put(testpath, fs, address)

    with open(address.path, 'rb') as fileobj:
        assert fileobj.read() == fileio.read()


def test_shed_put_file(testpath, filepath):
    fs = shed.Shed(str(testpath))
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
def test_shed_put_extension(testpath, stringio, extension):
    fs = shed.Shed(str(testpath))
    address = fs.put(stringio, extension)

    assert_file_put(testpath, fs, address)
    assert os.path.sep in address.path
    assert os.path.splitext(address.path)[1].endswith(extension)


def test_shed_put_invalid(testpath):
    fs = shed.Shed(str(testpath))

    with pytest.raises(ValueError):
        fs.put('foo')
