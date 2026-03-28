.PHONY: help install dev test test-unit test-functional \
        lint format fix check generate docs-check ci clean

# ── Colours ─────────────────────────────────────────────────────────────────
BOLD  := \033[1m
RESET := \033[0m

# ── Helpers ──────────────────────────────────────────────────────────────────
PYTHON := uv run

# ── Default target ───────────────────────────────────────────────────────────
help:                                                ## Show this help
	@printf "$(BOLD)MarkProof — available targets$(RESET)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BOLD)%-20s$(RESET) %s\n", $$1, $$2}'
	@printf "\n"

# ── Dependencies ─────────────────────────────────────────────────────────────
install:                                             ## Install core dependencies
	uv sync

dev:                                                 ## Install core + dev dependencies
	uv sync --dev

# ── Tests ─────────────────────────────────────────────────────────────────────
test:                                                ## Run the full test suite
	$(PYTHON) pytest

test-unit:                                           ## Run unit tests only
	$(PYTHON) pytest tests/unit/ -v

test-functional:                                     ## Run functional tests only
	$(PYTHON) pytest tests/functional/ -v

test-cov:                                            ## Run tests with coverage report
	$(PYTHON) pytest --cov=src/markproof --cov-report=term-missing

# ── Code quality ──────────────────────────────────────────────────────────────
lint:                                                ## Check code with ruff (no changes)
	$(PYTHON) ruff check .

format:                                              ## Check formatting with ruff (no changes)
	$(PYTHON) ruff format --check .

fix:                                                 ## Apply ruff lint fixes and auto-format
	$(PYTHON) ruff check --fix .
	$(PYTHON) ruff format .

check: lint format                                   ## Run lint + format checks (CI-safe, no writes)

# ── Documentation ─────────────────────────────────────────────────────────────
generate:                                            ## Regenerate README from source tree
	$(PYTHON) markproof generate .

docs-check:                                          ## Validate README and docs library
	$(PYTHON) markproof check README.md --root .
	@for doc in docs/*.md; do \
	  printf "  checking $$doc ...\n"; \
	  $(PYTHON) markproof check "$$doc" --root docs/; \
	done

# ── Full pipeline ─────────────────────────────────────────────────────────────
ci:                                                  ## Full CI pipeline: fix → test → generate → docs-check
	$(MAKE) fix
	$(MAKE) test
	$(MAKE) generate
	$(MAKE) docs-check

# ── Housekeeping ─────────────────────────────────────────────────────────────
clean:                                               ## Remove caches and build artefacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache  -exec rm -rf {} +
	find . -type d -name dist         -exec rm -rf {} +
	find . -name "*.pyc" -delete
	@printf "$(BOLD)clean$(RESET) — done\n"
