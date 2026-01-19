<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/logo-dark.svg">
  <img alt="unwrappy" src="docs/assets/logo-dark.svg" width="80">
</picture>

# unwrappy

[![PyPI](https://img.shields.io/pypi/v/unwrappy?style=for-the-badge&colorA=d2ccb8&colorB=423e31)](https://pypi.org/project/unwrappy/)
[![Python](https://img.shields.io/pypi/pyversions/unwrappy?style=for-the-badge&colorA=d2ccb8&colorB=423e31)](https://pypi.org/project/unwrappy/)
[![License](https://img.shields.io/badge/license-MIT-423e31?style=for-the-badge&colorA=d2ccb8&colorB=423e31)](https://github.com/leodiegues/unwrappy/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/leodiegues/unwrappy/test.yml?label=tests&style=for-the-badge&colorA=d2ccb8&colorB=423e31)](https://github.com/leodiegues/unwrappy/actions/workflows/test.yml)

Rust-inspired `Result` and `Option` types for Python, enabling safe, expressive error handling with errors as values.

## Installation

```bash
pip install unwrappy
```

## Quick Start

```python
from unwrappy import Ok, Err, Result

def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Err("division by zero")
    return Ok(a / b)

# Pattern matching (Python 3.10+)
match divide(10, 2):
    case Ok(value):
        print(f"Result: {value}")
    case Err(error):
        print(f"Error: {error}")

# Combinator chaining
result = (
    divide(10, 2)
    .map(lambda x: x * 2)
    .and_then(lambda x: Ok(int(x)) if x < 100 else Err("too large"))
)
```

## Why unwrappy?

- **Explicit error handling**: No hidden exceptions, errors are values
- **Type-safe**: Full generic type support with proper inference
- **Functional**: Rich combinator API (map, and_then, or_else, etc.)
- **Async-first**: LazyResult for clean async operation chaining
- **Pattern matching**: Works with Python 3.10+ structural matching

## Core Types

### Result[T, E]

A type that represents either success (`Ok`) or failure (`Err`).

```python
from unwrappy import Ok, Err, Result

# Success
ok: Result[int, str] = Ok(42)
ok.unwrap()      # 42
ok.is_ok()       # True

# Error
err: Result[int, str] = Err("failed")
err.unwrap_err() # "failed"
err.is_err()     # True
```

### LazyResult[T, E]

For async operation chaining without nested awaits:

```python
from unwrappy import LazyResult, Ok, Err

async def fetch_user(id: int) -> Result[dict, str]: ...
async def fetch_profile(user: dict) -> Result[dict, str]: ...

# Clean async chaining - no nested awaits!
result = await (
    LazyResult.from_awaitable(fetch_user(42))
    .and_then(fetch_profile)
    .map(lambda p: p["name"])
    .map(str.upper)
    .collect()
)
```

### Option[T]

A type that represents an optional value: either `Some(value)` or `Nothing`.

```python
from unwrappy import Some, NOTHING, Option, from_nullable

# Has value
some: Option[int] = Some(42)
some.unwrap()      # 42
some.is_some()     # True

# No value
nothing: Option[int] = NOTHING
nothing.is_nothing()  # True

# From nullable Python value
value: str | None = get_optional_value()
opt = from_nullable(value)  # Some(value) or NOTHING
```

### LazyOption[T]

For async operation chaining on optional values:

```python
from unwrappy import LazyOption, Some

async def fetch_config(key: str) -> Option[str]: ...
async def parse_value(s: str) -> Option[int]: ...

# Clean async chaining
result = await (
    LazyOption.from_awaitable(fetch_config("timeout"))
    .and_then(parse_value)
    .map(lambda x: x * 1000)
    .collect()
)
```

## API Overview

### Result API

#### Transformation

| Method | Description |
|--------|-------------|
| `map(fn)` | Transform Ok value |
| `map_err(fn)` | Transform Err value |
| `and_then(fn)` | Chain Result-returning function |
| `or_else(fn)` | Recover from Err |

#### Extraction

| Method | Description |
|--------|-------------|
| `unwrap()` | Get value or raise UnwrapError |
| `unwrap_or(default)` | Get value or default |
| `unwrap_or_else(fn)` | Get value or compute default |
| `unwrap_or_raise(fn)` | Get value or raise custom exception from fn(error) |
| `expect(msg)` | Get value or raise with message |

#### Inspection

| Method | Description |
|--------|-------------|
| `is_ok()` / `is_err()` | Check variant |
| `ok()` / `err()` | Convert to Option |
| `tee(fn)` / `inspect(fn)` | Side effect on Ok |
| `inspect_err(fn)` | Side effect on Err |

#### Utilities

| Function/Method | Description |
|-----------------|-------------|
| `flatten()` | Unwrap nested Result |
| `split()` | Convert to (value, error) tuple |
| `filter(predicate, error)` | Keep Ok if predicate passes |
| `zip(other)` / `zip_with(other, fn)` | Combine two Results |
| `context(error)` | Add context to errors |
| `sequence_results(results)` | Collect Results into Result |
| `traverse_results(items, fn)` | Map and collect |

### Option API

#### Transformation

| Method | Description |
|--------|-------------|
| `map(fn)` | Transform Some value |
| `map_or(default, fn)` | Transform or return default |
| `map_or_else(default_fn, fn)` | Transform or compute default |
| `and_then(fn)` | Chain Option-returning function |
| `or_else(fn)` | Recover from Nothing |
| `filter(predicate)` | Keep value if predicate passes |

#### Extraction

| Method | Description |
|--------|-------------|
| `unwrap()` | Get value or raise UnwrapError |
| `unwrap_or(default)` | Get value or default |
| `unwrap_or_else(fn)` | Get value or compute default |
| `unwrap_or_raise(exc)` | Get value or raise exception |
| `expect(msg)` | Get value or raise with message |

#### Inspection

| Method | Description |
|--------|-------------|
| `is_some()` / `is_nothing()` | Check variant |
| `tee(fn)` / `inspect(fn)` | Side effect on Some |
| `inspect_nothing(fn)` | Side effect on Nothing |

#### Utilities

| Function/Method | Description |
|-----------------|-------------|
| `from_nullable(value)` | Convert None to Nothing |
| `flatten()` | Unwrap nested Option |
| `zip(other)` / `zip_with(other, fn)` | Combine two Options |
| `xor(other)` | Exactly one must be Some |
| `ok_or(err)` / `ok_or_else(fn)` | Convert to Result |
| `to_tuple()` | Convert to single-element tuple |
| `sequence_options(options)` | Collect Options into Option |
| `traverse_options(items, fn)` | Map and collect |

## Examples

### Error Recovery

```python
def get_config(key: str) -> Result[str, str]:
    return Err(f"missing: {key}")

# Recover with default
value = get_config("port").unwrap_or("8080")

# Recover with computation
value = (
    get_config("port")
    .or_else(lambda e: Ok("8080"))
    .unwrap()
)
```

### Chaining Operations

```python
def parse_int(s: str) -> Result[int, str]:
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"invalid number: {s}")

def validate_positive(n: int) -> Result[int, str]:
    return Ok(n) if n > 0 else Err("must be positive")

result = (
    parse_int("42")
    .and_then(validate_positive)
    .map(lambda x: x * 2)
)
# Ok(84)
```

### Async Operations with LazyResult

```python
async def fetch_user(id: int) -> Result[User, str]:
    # async database call
    ...

async def fetch_posts(user: User) -> Result[list[Post], str]:
    # async API call
    ...

# Build pipeline, execute once
result = await (
    LazyResult.from_awaitable(fetch_user(42))
    .and_then(fetch_posts)              # async
    .map(lambda posts: len(posts))      # sync
    .tee(lambda n: print(f"Found {n}")) # side effect
    .collect()
)
```

### Working with Optional Values

```python
from unwrappy import Some, NOTHING, Option, from_nullable

# Convert nullable Python values
def get_user_email(user_id: int) -> str | None:
    # May return None if user has no email
    ...

email_opt = from_nullable(get_user_email(42))

# Chain operations on optional values
display_name = (
    email_opt
    .map(lambda e: e.split("@")[0])
    .map(str.title)
    .unwrap_or("Anonymous")
)

# Filter with predicates
valid_port = (
    Some(8080)
    .filter(lambda p: 1 <= p <= 65535)
    .unwrap_or(3000)
)

# Convert to Result for error context
result = (
    from_nullable(get_user_email(42))
    .ok_or("User has no email configured")
)
```

### Batch Processing

```python
from unwrappy import Ok, sequence_results, traverse_results

# Collect multiple Results
results = [Ok(1), Ok(2), Ok(3)]
combined = sequence_results(results)  # Ok([1, 2, 3])

# Map and collect
items = ["1", "2", "3"]
parsed = traverse_results(items, parse_int)  # Ok([1, 2, 3])
```

```python
from unwrappy import Some, NOTHING, sequence_options, traverse_options, from_nullable

# Collect multiple Options
options = [Some(1), Some(2), Some(3)]
combined = sequence_options(options)  # Some([1, 2, 3])

# Fails fast if any is Nothing
options_with_nothing = [Some(1), NOTHING, Some(3)]
combined = sequence_options(options_with_nothing)  # NOTHING

# Map nullable values and collect
items: list[int | None] = [1, 2, 3]
result = traverse_options(items, from_nullable)  # Some([1, 2, 3])
```

## Serialization

unwrappy supports JSON serialization for integration with task queues and workflow frameworks (Celery, Temporal, DBOS, etc.).

```python
from unwrappy import Ok, Err, Some, NOTHING, dumps, loads

# Serialize Result
encoded = dumps(Ok({"key": "value"}))
# '{"__unwrappy_type__": "Ok", "value": {"key": "value"}}'

# Serialize Option
encoded = dumps(Some(42))
# '{"__unwrappy_type__": "Some", "value": 42}'

encoded = dumps(NOTHING)
# '{"__unwrappy_type__": "Nothing"}'

# Deserialize
decoded = loads(encoded)  # Some(42), NOTHING, Ok(...), or Err(...)
```

For standard json module usage:

```python
import json
from unwrappy import ResultEncoder, result_decoder

encoded = json.dumps(Ok(42), cls=ResultEncoder)
decoded = json.loads(encoded, object_hook=result_decoder)
```

> **Note**: `LazyResult` and `LazyOption` cannot be serialized directly. Call `.collect()` first to get a concrete `Result` or `Option`.

See [ARCHITECTURE.md](ARCHITECTURE.md#serialization-support) for framework integration examples.

## License

MIT
