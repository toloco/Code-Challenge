#!make
################################################################################
# Makefile
################################################################################
.PHONY: help clean format lint test test-unit test-integration

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'

################################################################################

clean:  ## Remove all pyc and caches
	@find . -name '*.py[co]' -exec rm -f {} +
	@find . -name '.pytest_cache' -exec rm -fr {} +
	@find . -name '.ruff_cache' -exec rm -fr {} +
	@find . -name '__pycache__' -exec rm -fr {} +

format:  ## Format code with ruff
	@uv run ruff format .
	@uv run ruff check --fix .

lint:  ## Lint code with ruff
	@uv run ruff check .

test:  ## Run all tests with pytest
	@uv run pytest .

test-unit:  ## Run unit tests only (no API calls)
	@uv run pytest . -m "not integration"

test-integration:  ## Run integration tests only (real API calls)
	@uv run pytest . -m "integration" -v
