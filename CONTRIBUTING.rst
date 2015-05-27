Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

You can contribute in many ways:


Types of Contributions
----------------------

Report Bugs
+++++++++++

Report bugs at https://github.com/dgilland/hashfs/issues.

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.


Fix Bugs
++++++++

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever wants to implement it.


Implement Features
++++++++++++++++++

Look through the GitHub issues for features. Anything tagged with "enhancement" or "help wanted" is open to whoever wants to implement it.


Write Documentation
+++++++++++++++++++

HashFS could always use more documentation, whether as part of the official HashFS docs, in docstrings, or even on the web in blog posts, articles, and such.


Submit Feedback
+++++++++++++++

The best way to send feedback is to file an issue at https://github.com/dgilland/hashfs/issues.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are welcome :)


Get Started!
------------

Ready to contribute? Here's how to set up ``hashfs`` for local development.

1. Fork the ``hashfs`` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/hashfs.git

3. Install your local copy into a virtualenv. Assuming you have virtualenv installed, this is how you set up your fork for local development::

    $ cd hashfs
    $ make build

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass linting (`PEP8`_ and pylint) and the tests, including testing other Python versions with tox::

    $ make test-full

6. Add yourself to ``AUTHORS.rst``.

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website.


Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put your new functionality into a function with a docstring, and add the feature to the README.rst.
3. The pull request should work for Python 2.7, 3.3, and 3.4. Check https://travis-ci.org/dgilland/hashfs/pull_requests and make sure that the tests pass for all supported Python versions.


Project CLI
-----------

Some useful CLI commands when working on the project are below. **NOTE:** All commands are run from the root of the project and require ``make``.

make build
++++++++++

Run the ``clean`` and ``install`` commands.

::

    make build


make install
++++++++++++

Install Python dependencies into virtualenv located at ``env/``.

::

    make install


make clean
++++++++++

Remove build/test related temporary files like ``env/``, ``.tox``, ``.coverage``, and ``__pycache__``.

::

    make clean


make test
+++++++++

Run unittests under the virtualenv's default Python version. Does not test all support Python versions. To test all supported versions, see `make test-full`_.

::

    make test


make test-full
++++++++++++++

Run unittest and linting for all supported Python versions. **NOTE:** This will fail if you do not have all Python versions installed on your system. If you are on an Ubuntu based system, the `Dead Snakes PPA`_ is a good resource for easily installing multiple Python versions. If for whatever reason you're unable to have all Python versions on your development machine, note that Travis-CI will run full integration tests on all pull requests.

::

    make test-full


make lint
+++++++++

Run ``make pylint`` and ``make pep8`` commands.

::

    make lint


make pylint
+++++++++++

Run ``pylint`` compliance check on code base.

::

    make pylint


make pep8
+++++++++

Run `PEP8`_ compliance check on code base.

::

    make pep8


make docs
+++++++++

Build documentation to ``docs/_build/``.

::

    make docs


.. _Dead Snakes PPA: https://launchpad.net/~fkrull/+archive/deadsnakes
.. _PEP8: http://legacy.python.org/dev/peps/pep-0008/