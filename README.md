# unwrappy

Rust-inspired `Result` and `Option` types for Python, enabling safe, expressive error handling without exceptions.

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

## API Overview

### Transformation

| Method | Description |
|--------|-------------|
| `map(fn)` | Transform Ok value |
| `map_err(fn)` | Transform Err value |
| `and_then(fn)` | Chain Result-returning function |
| `or_else(fn)` | Recover from Err |

### Extraction

| Method | Description |
|--------|-------------|
| `unwrap()` | Get value or raise UnwrapError |
| `unwrap_or(default)` | Get value or default |
| `unwrap_or_else(fn)` | Get value or compute default |
| `unwrap_or_raise(fn)` | Get value or raise custom exception from fn(error) |
| `expect(msg)` | Get value or raise with message |

### Inspection

| Method | Description |
|--------|-------------|
| `is_ok()` / `is_err()` | Check variant |
| `ok()` / `err()` | Get Optional value |
| `tee(fn)` / `inspect(fn)` | Side effect on Ok |
| `inspect_err(fn)` | Side effect on Err |

### Utilities

| Function/Method | Description |
|-----------------|-------------|
| `flatten()` | Unwrap nested Result |
| `split()` | Convert to (value, error) tuple |
| `sequence(results)` | Collect Results into Result |
| `traverse(items, fn)` | Map and collect |

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

### Batch Processing

```python
from unwrappy import sequence, traverse

# Collect multiple Results
results = [Ok(1), Ok(2), Ok(3)]
combined = sequence(results)  # Ok([1, 2, 3])

# Map and collect
items = ["1", "2", "3"]
parsed = traverse(items, parse_int)  # Ok([1, 2, 3])
```

## Serialization

unwrappy supports JSON serialization for integration with task queues and workflow frameworks (Celery, Temporal, DBOS, etc.).

```python
from unwrappy import Ok, Err, dumps, loads

# Serialize
encoded = dumps(Ok({"key": "value"}))
# '{"__unwrappy_type__": "Ok", "value": {"key": "value"}}'

# Deserialize
decoded = loads(encoded)  # Ok({'key': 'value'})
```

For standard json module usage:

```python
import json
from unwrappy import ResultEncoder, result_decoder

encoded = json.dumps(Ok(42), cls=ResultEncoder)
decoded = json.loads(encoded, object_hook=result_decoder)
```

> **Note**: `LazyResult` cannot be serialized directly. Call `.collect()` first to get a concrete `Result`.

See [ARCHITECTURE.md](ARCHITECTURE.md#serialization-support) for framework integration examples.

## License

MIT
