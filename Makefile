.PHONY: install run webhook test lint format docker clean

PY ?= python3.11

install:
	$(PY) -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

install-dev: install
	./venv/bin/pip install -r requirements-dev.txt

run:
	./venv/bin/python main.py

webhook:
	./venv/bin/python main.py --webhook

test:
	./venv/bin/python -m pytest -q

lint:
	./venv/bin/python -m ruff check .
	./venv/bin/python -m compileall -q bot main.py

format:
	./venv/bin/python -m black --line-length 100 .
	./venv/bin/python -m ruff check --fix .

docker:
	docker build -t accounts_market .

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ bot/__pycache__
