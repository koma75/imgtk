.DEFAULT_GOAL := build
.PHONY: build freeze publish package publish pubtest clean venv install test
PROJ_NAME = imgtk
PY_VERSION = 3.11
SHELL = bash


build: venv
	uv pip install --editable .

freeze:
	pip freeze > requirements.txt

package: clean
	python setup.py sdist

publish: package
	twine upload dist/*

pubtest: package
	twine upload --repository pypitest dist/*

clean :
	rm -rf dist \
	rm -rf *.egg-info

venv:
	@uv venv --python $(PY_VERSION) .venv

install:
	@uv pip install -r requirements.txt

test:
	@uv run test_harness.py

