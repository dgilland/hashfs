##
# Variables
##

ENV_NAME = env
ENV_ACT = . env/bin/activate;
PIP = $(ENV_NAME)/bin/pip
PYTEST_ARGS = --doctest-modules -v -s
PYTEST_TARGET = hashfs tests
COVERAGE_ARGS = --cov-config setup.cfg --cov-report term-missing --cov
COVERAGE_TARGET = hashfs


##
# Targets
##

.PHONY: build
build: clean install

.PHONY: clean
clean: clean-env clean-files

.PHONY: clean-env
clean-env:
	rm -rf $(ENV_NAME)

.PHONY: clean-files
clean-files:
	rm -rf .tox
	rm -rf .coverage
	find . -name \*.pyc -type f -delete
	find . -name \*.test.db -type f -delete
	find . -depth -name __pycache__ -type d -exec rm -rf {} \;
	rm -rf dist *.egg* build

.PHONY: install
install:
	rm -rf $(ENV_NAME)
	virtualenv --no-site-packages $(ENV_NAME)
	$(PIP) install -r requirements.txt

.PHONY: test
test: flake8 pytest

.PHONY: pytest
pytest:
	$(ENV_ACT) py.test $(PYTEST_ARGS) $(COVERAGE_ARGS) $(COVERAGE_TARGET) $(PYTEST_TARGET)

.PHONY: test-full
test-full: pylint-errors test-setuppy clean-files

.PHONY: test-setuppy
test-setuppy:
	python setup.py test

.PHONY: lint
lint: flake8

.PHONY: flake8
flake8:
	$(ENV_ACT) flake8 $(PYTEST_TARGET)

.PHONY: master
master:
	git checkout master
	git merge develop
	git push origin develop master --tags
	git checkout develop

.PHONY: release
release:
	$(ENV_ACT) python setup.py sdist bdist_wheel
	$(ENV_ACT) twine upload dist/*
	rm -rf dist *.egg* build

.PHONY: docs
docs:
	touch docs/_build
	rm -r docs/_build
	$(ENV_ACT) cd docs; make doctest
	$(ENV_ACT) cd docs; make html

.PHONY: serve-docs
serve-docs:
	cd docs/_build/html; python2 -m SimpleHTTPServer 8000

.PHONY: reload-docs
reload-docs: docs serve-docs


##
# TravisCI
##

.PHONY: travisci-install
travisci-install:
	pip install -r requirements.txt

.PHONY: travisci-test
travisci-test:
	flake8 $(PYTEST_TARGET)
	py.test $(PYTEST_ARGS) $(COVERAGE_ARGS) $(COVERAGE_TARGET) $(PYTEST_TARGET)
