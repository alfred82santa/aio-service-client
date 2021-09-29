
PACKAGE_NAME = aio-service-client
PACKAGE_COVERAGE = service_client

help:
	@echo "Options"
	@echo "-----------------------------------------------------------------------"
	@echo "help:                     This help"
	@echo "requirements:             Download requirements"
	@echo "requirements-test:        Download requirements for tests"
	@echo "requirements-docs:        Download requirements for docs"
	@echo "run-tests:                Run tests with coverage"
	@echo "publish:                  Publish new version on Pypi"
	@echo "clean:                    Clean compiled files"
	@echo "flake:                    Run Flake8"
	@echo "prepush:                  Helper to run before to push to repo"
	@echo "pull-request:             Helper to run before to merge a pull request"
	@echo "autopep:                  Reformat code using PEP8"
	@echo "-----------------------------------------------------------------------"

requirements:
	@echo "Installing ${PACKAGE_NAME} requirements..."
	pip install -r requirements.txt

requirements-test: requirements
	@echo "Installing ${PACKAGE_NAME} tests requirements..."
	pip install -r requirements-test.txt

requirements-docs: requirements
	@echo "Installing ${PACKAGE_NAME} docs requirements..."
	pip install -r requirements-docs.txt

run-tests:
	@echo "Running tests..."
	nosetests --with-coverage -d --cover-package=${PACKAGE_COVERAGE} --cover-erase

build:
	python setup.py bdist_wheel

publish: clean build
	@echo "Publishing new version on Pypi..."
	twine upload dist/*

clean:
	@echo "Cleaning compiled files..."
	find . | grep -E "(__pycache__|\.pyc|\.pyo)$ " | xargs rm -rf
	rm -rf dist
	rm -rf *.egg-info
	rm -rf build

flake:
	@echo "Running flake8 tests..."
	flake8 ${PACKAGE_COVERAGE}
	flake8 tests

autopep:
	autopep8 --max-line-length 120 -r -j 8 -i .

prepush: flake run-tests

pull-request: flake run-tests
