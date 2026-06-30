# Development

## Quick Start

```bash
git clone https://github.com/zopyx/pp.server
cd pp.server
uv venv --python 3.12
uv sync --all-extras
make test
```

## Project Structure

```
pp/server/
├── cli.py              # Click CLI entry point (pp-server command)
├── server.py           # FastAPI application + routes
├── converters.py       # PDF conversion orchestration + config
├── registry.py         # Converter registration (PATH detection)
├── models.py           # Pydantic response models
├── util.py             # Shell execution, sanitization, utilities
├── logger.py           # Loguru logger singleton
├── templates.py        # Circus/hypercorn config file generation
├── config.toml         # Converter command definitions
├── static/             # Web UI assets (CSS, images, favicon)
├── templates/          # Jinja2 web templates
├── _templates/         # Server config templates (circusd, hypercorn)
├── test_data/          # Sample HTML/XML for self-test
└── tests/              # pytest test suite

docker/                 # Dockerfiles for various converter combos
scripts/                # Utility scripts (generate_openapi.py, etc.)
docs/                   # Sphinx documentation source
```

## Commands

| Command | Purpose |
|---|---|
| `make test` | Run tests |
| `make lint` | Ruff linting |
| `make type-check` | Ty type checking |
| `make quality` | All quality gates (lint + type + test) |
| `make sast` | Security scan (bandit) |
| `make coverage` | Tests with HTML coverage report |
| `make serve` | Start dev server (hypercorn, reload) |
| `make build` | Build distribution (uv build) |
| `make format` | Auto-format code |

## Tech Stack

| Tool | Purpose |
|---|---|
| **uv** | Package & virtual env manager |
| **ruff** | Linter + formatter (13 rule sets) |
| **ty** | Type checker (Astral, Rust-based) |
| **pytest** | Test runner with coverage |
| **pre-commit** | Git hooks (ruff + ty + bandit) |
| **hatchling** | Build backend (via pyproject.toml) |

## Testing

```bash
make test           # quick run
make coverage       # run with HTML report
uv run pytest -v -k "selftest"  # specific tests
```

Tests use `pytest-cov` for coverage and `pytest-asyncio` for async tests.
Mock external converters with `monkeypatch` and `AsyncMock`.

## Type Checking

```bash
make type-check     # run ty on the whole project
uv run ty check     # same, with verbose output
```

Ty is configured via `pyproject.toml` (no extra config needed).
Inline suppressions: `# ty: ignore`.

## CI Pipeline

The CI workflow (`.github/workflows/ci.yml`) runs on every push:

1. **Lint** — `ruff check .`
2. **Format check** — `ruff format --check .`
3. **Type check** — `ty check`
4. **Security scan** — `bandit`
5. **Test** — `pytest` with coverage

Python versions: 3.12, 3.13, 3.14 (via prebuilt wheels).

## Release

```bash
# Bump version in pyproject.toml
# Update CHANGES.rst
git commit -m "release: X.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The tag triggers the release workflow (`.github/workflows/release.yml`) which
builds and publishes to PyPI.
