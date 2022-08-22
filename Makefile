# development
devenv:
	python -m venv venv
	source venv/bin/activate
	pip install -r devtools/dev-requirements.txt

ci:
	pytest


# packaging
build:
	python -m build

publish-test:
	twine upload -r testpypi dist/*

publish:
	twine upload dist/*
