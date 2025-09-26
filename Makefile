# pp.server Makefile
# Modern Python development workflow using uv

.PHONY: help install dev-install test lint format type-check clean build docs serve release
.DEFAULT_GOAL := help

# Variables
PYTHON := python
UV := uv
PROJECT_NAME := pp.server
DOCS_DIR := docs
BUILD_DIR := dist
TEST_DIR := pp/server/tests

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install project dependencies
	$(UV) sync

dev-install: ## Install development dependencies
	$(UV) sync --all-extras
	$(UV) pip install -e .

test: ## Run tests with pytest
	$(UV) run pytest $(TEST_DIR) -v

test-coverage: ## Run tests with coverage
	$(UV) run pytest $(TEST_DIR) --cov=pp.server --cov-report=html --cov-report=term-missing

lint: ## Run linting checks
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Format code
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

type-check: ## Run type checking
	$(UV) run mypy pp/server

quality: lint type-check ## Run all quality checks

clean: ## Clean build artifacts
	rm -rf $(BUILD_DIR)/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	$(UV) build

docs: ## Build documentation
	@if [ -d "$(DOCS_DIR)" ]; then \
		cd $(DOCS_DIR) && make html; \
	else \
		echo "No docs directory found"; \
	fi

serve: ## Start development server
	$(UV) run hypercorn pp.server.server:app --bind 0.0.0.0:8000 --reload

serve-prod: ## Start production server
	$(UV) run hypercorn pp.server.server:app --bind 0.0.0.0:8000

check-converters: ## Check available PDF converters
	$(UV) run python -c "from pp.server import registry; registry.main()"

selftest: ## Run converter self-tests (requires converters installed)
	@echo "Available converters:"
	@$(UV) run python -c "from pp.server.registry import available_converters; print('\\n'.join(available_converters()))"

# Development workflow commands
dev-setup: dev-install ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make serve' to start the development server"

ci: quality test ## Run CI pipeline (quality checks + tests)

pre-commit: format quality test ## Run pre-commit checks

# Release management
check-release: ## Check if ready for release
	$(UV) run python -c "import pp.server; print(f'Current version: {pp.server.__version__ if hasattr(pp.server, \"__version__\") else \"Unknown\"}')" || echo "Version check failed"
	@echo "Checking build..."
	@$(MAKE) build
	@echo "Checking tests..."
	@$(MAKE) test

release-test: build ## Upload to test PyPI
	$(UV) run twine upload --repository testpypi $(BUILD_DIR)/*

release: build ## Upload to PyPI
	$(UV) run twine upload $(BUILD_DIR)/*

publish: ## Publish to PyPI using uv
	$(UV) publish

# Docker support (if needed)
docker-build: ## Build Docker image
	docker build -t $(PROJECT_NAME):latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 $(PROJECT_NAME):latest

# Utility commands
requirements: ## Generate requirements.txt from pyproject.toml
	$(UV) pip compile pyproject.toml -o requirements.txt

lock: ## Update lock file
	$(UV) lock

sync: ## Sync environment with lock file
	$(UV) sync

upgrade: ## Upgrade dependencies
	$(UV) lock --upgrade

show-deps: ## Show dependency tree
	$(UV) tree

# Info commands
info: ## Show project info
	@echo "Project: $(PROJECT_NAME)"
	@echo "Python: $$($(UV) run python --version)"
	@echo "UV: $$($(UV) --version)"
	@$(UV) run python -c "from pp.server.converters import CONVERTERS; print(f'Configured converters: {len(CONVERTERS)}')"