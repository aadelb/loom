# Contributing to Loom

Thank you for your interest in contributing to Loom! This guide explains how to set up your development environment, run tests, and submit contributions.

## Development Setup

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/aadelb/loom
cd loom
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,stealth]"
playwright install chromium firefox
python -m camoufox fetch
```

## Running Tests

Run the full test suite:

```bash
pytest tests/
```

With coverage report:

```bash
pytest tests/ --cov=src/loom --cov-report=term-missing
```

Skip integration tests that require live network calls:

```bash
pytest tests/ -k "not integration"
```

## Linting and Type Checking

Check code style:

```bash
ruff check src tests
```

Auto-format code:

```bash
ruff format src tests
```

Type checking:

```bash
mypy src
```

## Pre-commit Hooks

Install pre-commit hooks to catch issues before commits:

```bash
pre-commit install
```

## How to Add a New MCP Tool

1. Define parameter schema in `src/loom/params.py` as a Pydantic model
2. Create a new file under `src/loom/tools/` with the tool implementation
3. Register it in `src/loom/server.py` using the `@mcp.tool()` decorator
4. Add tests under `tests/test_tools/`
5. Add documentation under `docs/tools/`
6. Add CLI subcommand in `src/loom/cli.py` if the tool is user-facing

## How to Add a New LLM Provider

1. Create `src/loom/providers/<name>.py` subclassing `loom.providers.base.LLMProvider`
2. Implement required methods: `chat()`, `embed()`, `available()`, `close()`
3. Register in `src/loom/providers/__init__.py` and update `src/loom/config.py` `LLM_CASCADE_ORDER`
4. Add mocked tests under `tests/test_providers/`
5. Document the provider under `docs/providers/<name>.md`

## Commit Message Format

Use Conventional Commits:

- `feat: add research_foo tool` — new feature
- `fix: handle empty response from Exa` — bug fix
- `docs: clarify session lifecycle` — documentation
- `test: add fixture for Tavily cascade` — test additions
- `chore: bump dependencies` — maintenance
- `refactor: extract cache layer` — code reorganization

## Pull Request Checklist

Before submitting a PR:

- [ ] Tests added or updated
- [ ] `ruff check src tests` passes
- [ ] `mypy src` passes
- [ ] Documentation updated if user-facing change
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] PR description explains the what and why

## Code Style

We follow PEP 8 with these conventions:

- Type hints on all function signatures
- Async/await for I/O-bound operations
- Immutable data structures where possible
- Error handling at system boundaries
- Tests at 80%+ coverage

## Questions?

Open an issue on GitHub or check the documentation in `docs/`.
