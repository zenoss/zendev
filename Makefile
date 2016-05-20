.PHONY: clean-pyc clean-build docs

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "testall - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "sdist - package"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

lint:
	flake8 zendev tests

test:
	python setup.py test

test-all:
	tox

coverage:
	coverage run --source zendev setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

docs/_themes:
	mkdir -p docs/_themes

docs/_themes/bootstrap.zip: docs/_themes
	wget --no-check-certificate -O docs/_themes/bootstrap.zip \
		https://github.com/downloads/ryan-roemer/sphinx-bootstrap-theme/bootstrap.zip

_docs: docs/_themes/bootstrap.zip
	rm -f docs/zendev.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ zendev
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

docs: _docs
	open docs/_build/html/index.html

docker-docs:
	docker build -t zenoss/zendev-docs-build .
	docker run --rm -v $${PWD}:/zendev zenoss/zendev-docs-build bash -c "cd /zendev; pip install -e .; make _docs; chown -R $$(id -u) /zendev/docs"

publish-docs: 
	rm -rf /tmp/zendev-docs
	mv docs/_build/html /tmp/zendev-docs
	git checkout gh-pages
	git fetch origin gh-pages
	git merge --strategy-option theirs origin/gh-pages
	rm -rf *
	mv /tmp/zendev-docs/* .
	touch .nojekyll && git add .nojekyll
	git add --all && git commit -m "Docs update" && git push origin gh-pages
	git checkout develop

#release: clean
#	python setup.py sdist upload

sdist: clean
	python setup.py sdist
	ls -l dist
