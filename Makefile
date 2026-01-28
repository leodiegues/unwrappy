.DEFAULT_GOAL := help

.PHONY: .uv
.uv: ## Check that uv is installed
	@uv --version || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: .prek
.prek: ## Check that pre-commit is installed
	@prek -V || echo 'Please install prek: https://prek.j178.dev/installation/'

.PHONY: install
install: .uv .prek ## Install the package, dependencies, and pre-commit for local development
	uv sync --frozen --all-extras
	prek install --install-hooks

.PHONY: sync
sync: .uv ## Update local packages and uv.lock
	uv sync --all-extras

.PHONY: format
format: ## Format the code
	uv run ruff format
	uv run ruff check --fix --fix-only

.PHONY: lint
lint: ## Lint the code
	uv run ruff format --check
	uv run ruff check

.PHONY: typecheck-ty
typecheck-ty:
	uv run ty check

.PHONY: typecheck-pyright
typecheck-pyright:
	PYRIGHT_PYTHON_IGNORE_WARNINGS=1 uv run pyright

.PHONY: typecheck-mypy
typecheck-mypy:
	uv run mypy

.PHONY: typecheck
typecheck: typecheck-ty ## Run static type checking

.PHONY: typecheck-all  ## Run static type checking with ty, Pyright and Mypy
typecheck-all: typecheck-ty typecheck-pyright typecheck-mypy

.PHONY: test
test: ## Run tests and collect coverage data
	COLUMNS=150 uv run pytest

.PHONY: testcov
testcov: test ## Run tests and generate an HTML coverage report
	@echo "building coverage html"
	@uv run coverage html

.PHONY: all
all: format lint typecheck testcov ## Run code formatting, linting, static type checks, and tests with coverage report generation

.PHONY: help
help: ## Show this help (usage: make help)
	@echo "Usage: make [recipe]"
	@echo "Recipes:"
	@awk '/^[a-zA-Z0-9_-]+:.*?##/ { \
		helpMessage = match($$0, /## (.*)/); \
		if (helpMessage) { \
			recipe = $$1; \
			sub(/:/, "", recipe); \
			printf "  \033[36m%-20s\033[0m %s\n", recipe, substr($$0, RSTART + 3, RLENGTH); \
		} \
	}' $(MAKEFILE_LIST)
