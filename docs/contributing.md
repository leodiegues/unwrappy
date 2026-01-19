# Contributing

Thank you for your interest in contributing to unwrappy! This guide will help you get started with development.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/leodiegues/unwrappy.git
cd unwrappy

# Install dependencies
make install
```

## Development Commands

| Command | Purpose |
|---------|---------|
| `make test` | Run all tests |
| `make lint` | Lint code with ruff |
| `make format` | Format code with ruff |
| `make typecheck` | Type check with pyright, mypy, and ty |
| `make all` | Run format, lint, typecheck, and tests |
| `make help` | Show all available commands |

### Running Specific Tests

```bash
# Single test
uv run pytest tests/test_result.py::test_ok_map

# Test file
uv run pytest tests/test_result.py

# With verbose output
uv run pytest -vv tests/test_result.py
```

### Building Documentation

```bash
# Install docs dependencies
uv sync --group docs

# Serve locally with live reload
uv run mkdocs serve

# Build static site
uv run mkdocs build
```

## Code Style Guidelines

### General

- **Line length**: 120 characters maximum
- **Quotes**: Double quotes for strings
- **Docstrings**: Google-style format

### Type Annotations

All public APIs must have complete type annotations:

```python
def map(self, fn: Callable[[T], U]) -> Ok[U]:
    """Transform the Ok value using the provided function.

    Args:
        fn: Function to apply to the contained value.

    Returns:
        A new Ok containing the transformed value.
    """
    return Ok(fn(self._value))
```

### Docstrings

Use Google-style docstrings:

```python
def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
    """Chain a Result-returning function.

    Also known as "flatMap" or "bind" in functional programming.

    Args:
        fn: Function that takes the Ok value and returns a new Result.

    Returns:
        The Result returned by fn if self is Ok, otherwise self unchanged.

    Example:
        >>> Ok(5).and_then(lambda x: Ok(x * 2))
        Ok(10)
        >>> Err("e").and_then(lambda x: Ok(x * 2))
        Err("e")
    """
```

### Imports

Imports are sorted automatically by ruff:

```python
# Standard library
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

# Local
from unwrappy.exceptions import UnwrapError
```

## Testing Requirements

### Coverage

- All new features must include tests
- Maintain high test coverage (currently 99%)
- Tests run across Python 3.10-3.14 on Linux, macOS, and Windows

### Test Structure

```python
# tests/test_result.py

def test_ok_map_transforms_value():
    """map() should transform Ok values."""
    result = Ok(5).map(lambda x: x * 2)
    assert result == Ok(10)

def test_err_map_passes_through():
    """map() should not transform Err values."""
    result = Err("error").map(lambda x: x * 2)
    assert result == Err("error")

@pytest.mark.asyncio
async def test_ok_map_async():
    """map_async() should work with async functions."""
    async def double(x: int) -> int:
        return x * 2

    result = await Ok(5).map_async(double)
    assert result == Ok(10)
```

### Running Full Test Suite

Before submitting a PR:

```bash
make all
```

This runs:

1. Code formatting
2. Linting
3. Type checking (pyright, mypy, ty)
4. Tests with coverage

## Pull Request Process

### 1. Fork and Branch

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/unwrappy.git
cd unwrappy
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code with tests
- Update documentation if needed
- Follow code style guidelines

### 3. Run Checks

```bash
make all
```

### 4. Commit

Write clear commit messages:

```
Add filter() method to Result

- Adds filter(predicate, error) method to Ok and Err
- Returns Err with provided error if predicate fails on Ok value
- Err values pass through unchanged
- Includes tests and documentation
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub against the `main` branch.

### PR Requirements

- [ ] All CI checks pass
- [ ] Tests added for new features
- [ ] Documentation updated if needed
- [ ] No decrease in test coverage

## Project Structure

```
unwrappy/
├── src/unwrappy/
│   ├── __init__.py      # Public API exports
│   ├── result.py        # Result[T, E] type
│   ├── option.py        # Option[T] type
│   ├── exceptions.py    # UnwrapError, ChainedError
│   └── serde.py         # JSON serialization
├── tests/
│   ├── test_result.py
│   ├── test_option.py
│   └── test_serde.py
├── docs/                # Documentation (MkDocs)
├── examples/            # Usage examples
├── pyproject.toml       # Project configuration
└── Makefile            # Development commands
```

## Adding New Features

### 1. Consider the Design

Before implementing, consider:

- Does this fit unwrappy's design philosophy?
- Is it commonly needed?
- Can it be composed from existing methods?

### 2. Implement in Both Variants

Methods on Result/Option need implementations in both variants:

```python
# In Ok class
def new_method(self, ...) -> ...:
    # Ok-specific implementation
    ...

# In Err class
def new_method(self, ...) -> ...:
    # Err-specific implementation (often pass-through)
    ...
```

### 3. Add Async Variant if Needed

If the method takes a callable that could be async:

```python
async def new_method_async(self, fn: Callable[..., Awaitable[...]]) -> ...:
    ...
```

### 4. Update Exports

Add to `src/unwrappy/__init__.py`:

```python
__all__ = [
    ...,
    "new_method",  # if it's a standalone function
]
```

### 5. Document

- Add docstring with example
- Update relevant guide page
- Add to API reference if public

## Questions?

If you have questions or need help:

- Open an issue on [GitHub](https://github.com/leodiegues/unwrappy/issues)
- Check existing issues and discussions

Thank you for contributing!
