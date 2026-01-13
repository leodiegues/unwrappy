# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

unwrappy is a Python library providing Rust-inspired `Result` and `Option` types for safe, expressive error handling with errors as values.

## Development Commands

```bash
# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_file.py::test_name

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run ty check
```

## Architecture

The library provides two main types in `src/unwrappy/`:

- **Result** (`result.py`): A sum type with `Ok(T)` and `Err(E)` variants for operations that can fail
- **Option** (`option.py`): A sum type with `Some(T)` and `None` variants for optional values

Both types support:
- Pattern matching via `__match_args__`
- Functional combinators (`map`, `and_then`, `or_else`, etc.)
- Async variants of combinators (`map_async`, `and_then_async`, etc.)
- Safe unwrapping with `unwrap_or`, `unwrap_or_else`, `expect`

`exceptions.py` defines `UnwrapError`, raised when unwrapping fails (e.g., calling `unwrap()` on `Err`).
