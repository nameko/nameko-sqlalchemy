test: flake8 pylint pytest

flake8:
	flake8 nameko_sqlalchemy test

pylint:
	pylint nameko_sqlalchemy -E

pytest:
	coverage run --concurrency=eventlet --source nameko_sqlalchemy --branch -m pytest test
	coverage report --show-missing --fail-under=100
