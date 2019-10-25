#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


meta = {}
exec(read("hashfs/__meta__.py"), meta)

readme = read("README.rst")
changes = read("CHANGES.rst")


if sys.version_info < (3, 5):
    # Install back port of faster os.walk/scandir implementation.
    meta["__install_requires__"].append("scandir>=1.1")


class Tox(TestCommand):
    user_options = [("tox-args=", "a", "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = "-c tox.ini"

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # Import here because outside the eggs aren't loaded.
        import tox
        import shlex

        errno = tox.cmdline(args=shlex.split(self.tox_args))
        sys.exit(errno)


setup(
    name=meta["__title__"],
    version=meta["__version__"],
    url=meta["__url__"],
    license=meta["__license__"],
    author=meta["__author__"],
    author_email=meta["__email__"],
    description=meta["__summary__"],
    long_description=readme + "\n\n" + changes,
    packages=find_packages(exclude=["tests"]),
    install_requires=meta["__install_requires__"],
    tests_require=meta["__tests_require__"],
    cmdclass={"test": Tox},
    test_suite="tests",
    keywords="hashfs hash file system content addressable fixed storage",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Filesystems",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
