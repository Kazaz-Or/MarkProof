.PHONY: help install dev test test-unit test-functional \
        lint type-check format fix check generate docs-check ci clean

BOLD  := \033[1m
RESET := \033[0m

PYTHON := uv run

help:                                                ## Show this help
	@printf "$(BOLD)MarkProof — available targets$(RESET)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BOLD)%-20s$(RESET) %s\n", $$1, $$2}'
	@printf "\n"

install:                                             ## Install core dependencies
	uv sync

dev:                                                 ## Install core + dev dependencies
	uv sync --dev

test:                                                ## Run the full test suite
	$(PYTHON) pytest

test-unit:                                           ## Run unit tests only
	$(PYTHON) pytest tests/unit/ -v

test-functional:                                     ## Run functional tests only
	$(PYTHON) pytest tests/functional/ -v

test-cov:                                            ## Run tests with coverage report
	$(PYTHON) pytest --cov=src/markproof --cov-report=term-missing

type-check:                                          ## Run ty type checker
	$(PYTHON) ty check src/

lint:                                                ## Check code with ruff (no changes)
	$(PYTHON) ruff check .

format:                                              ## Check formatting with ruff (no changes)
	$(PYTHON) ruff format --check .

fix:                                                 ## Apply ruff lint fixes and auto-format
	$(PYTHON) ruff check --fix .
	$(PYTHON) ruff format .

check: lint type-check format                        ## Run lint + type-check + format checks (CI-safe, no writes)

generate:                                            ## Regenerate README from source tree
	$(PYTHON) markproof generate .

docs-check:                                          ## Validate README and docs library
	$(PYTHON) markproof check README.md --root .
	@for doc in docs/*.md; do \
	  printf "  checking $$doc ...\n"; \
	  $(PYTHON) markproof check "$$doc" --root docs/; \
	done

ci:                                                  ## Full CI pipeline: fix → type-check → test → generate → docs-check
	$(MAKE) fix
	$(MAKE) type-check
	$(MAKE) test
	$(MAKE) generate
	$(MAKE) docs-check

clean:                                               ## Remove caches and build artefacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache  -exec rm -rf {} +
	find . -type d -name dist         -exec rm -rf {} +
	find . -name "*.pyc" -delete
	@printf "$(BOLD)clean$(RESET) — done\n"
