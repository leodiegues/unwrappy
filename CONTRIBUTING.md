# Contributing to unwrappy

Thank you for your interest in contributing to unwrappy! This guide will help you get started with development.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Development Setup

```bash
# Clone and install (requires uv)
git clone https://github.com/leodiegues/unwrappy.git
cd unwrappy
make install
```

## Development Commands

| Command | Purpose |
|---------|---------|
| `make test` | Run all tests |
| `make lint` | Lint code |
| `make format` | Format code |
| `make typecheck` | Type check |
| `make all` | Run format, lint, typecheck, and tests with coverage |
| `make help` | Show all available commands |

For running a specific test, use: `uv run pytest tests/test_file.py::test_name`

## Code Style Guidelines

- **Line length**: 120 characters maximum
- **Quotes**: Double quotes for strings
- **Docstrings**: Google-style format
- **Imports**: Sorted automatically via ruff (isort rules)

All style checks are enforced by ruff and will be verified in CI.

## Testing Requirements

- All new features must include tests
- Maintain high test coverage (currently 99%)
- Tests run across Python 3.10-3.14 on Linux, macOS, and Windows

Run the full test suite before submitting:

```bash
make test
```

## Pull Request Process

1. **Fork** the repository and create a feature branch from `main`
2. **Make changes** with accompanying tests
3. **Run all checks locally**:
   ```bash
   make all
   ```
4. **Submit a PR** against the `main` branch
5. **CI must pass** (tests + code quality checks)

## Project Structure

```
src/unwrappy/
├── __init__.py      # Public API exports
├── result.py        # Result[T, E] type
├── option.py        # Option[T] type
├── exceptions.py    # UnwrapError, ChainedError
└── serde.py         # JSON serialization

tests/
├── test_result.py
├── test_option.py
└── test_serde.py

examples/
├── README.md
├── error_handling.py
├── option_handling.py
└── web_api.py
```

## Questions?

If you have questions or need help, feel free to open an issue on GitHub.
