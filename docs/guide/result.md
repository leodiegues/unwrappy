# Result Type

The `Result[T, E]` type represents an operation that can either succeed with a value of type `T` or fail with an error of type `E`.

## Overview

```python
from unwrappy import Ok, Err, Result

# Success case
ok: Result[int, str] = Ok(42)

# Error case
err: Result[int, str] = Err("something went wrong")
```

Result is a **union type** (type alias):

```python
Result[T, E] = Ok[T] | Err[E]
```

This means `Ok` and `Err` are separate classes, each with a single type parameter for precise type inference.

## Creating Results

### Success Variant (`Ok`)

```python
from unwrappy import Ok

# Simple value
result = Ok(42)  # Ok[int]

# Complex types
result = Ok({"name": "Alice", "age": 30})  # Ok[dict[str, Any]]
result = Ok([1, 2, 3])  # Ok[list[int]]
```

### Error Variant (`Err`)

```python
from unwrappy import Err

# String errors (simple)
result = Err("not found")  # Err[str]

# Structured errors (recommended for complex apps)
@dataclass
class ValidationError:
    field: str
    message: str

result = Err(ValidationError("email", "invalid format"))  # Err[ValidationError]
```

## Checking Variants

### Methods

```python
result = Ok(42)

result.is_ok()   # True
result.is_err()  # False
```

### Type Guard Functions

For proper type narrowing in early returns, use the standalone functions:

```python
from unwrappy import Ok, Err, Result, is_ok, is_err

def process(data: str) -> Result[int, str]:
    parsed = parse(data)  # Result[int, str]

    if is_err(parsed):
        return parsed  # Type checker knows this is Err[str]

    # Type checker knows parsed is Ok[int] here
    return Ok(parsed.unwrap() * 2)
```

!!! note "Why type guard functions?"
    Python's type system doesn't narrow types based on method return values. The `is_ok()` and `is_err()` methods work at runtime, but the standalone `is_ok(result)` and `is_err(result)` functions use `TypeIs` for proper type narrowing.

## Pattern Matching

The recommended way to handle Results (Python 3.10+):

```python
from unwrappy import Ok, Err, Result

def handle_result(result: Result[int, str]) -> str:
    match result:
        case Ok(value):
            return f"Success: {value}"
        case Err(error):
            return f"Error: {error}"
```

Pattern matching with guards:

```python
match result:
    case Ok(value) if value > 100:
        return "Large success"
    case Ok(value):
        return f"Success: {value}"
    case Err(error):
        return f"Error: {error}"
```

## Extracting Values

### Get Value or Raise

```python
Ok(42).unwrap()      # 42
Err("oops").unwrap() # Raises UnwrapError
```

!!! danger "Use with caution"
    `unwrap()` raises `UnwrapError` if called on an `Err`. Only use when you're certain the Result is `Ok`, or in tests.

### Get Error or Raise

```python
Err("oops").unwrap_err()  # "oops"
Ok(42).unwrap_err()       # Raises UnwrapError
```

### With Default

```python
Ok(42).unwrap_or(0)       # 42
Err("oops").unwrap_or(0)  # 0
```

### With Computed Default

```python
Ok(42).unwrap_or_else(lambda e: len(e))       # 42
Err("oops").unwrap_or_else(lambda e: len(e))  # 4
```

### Convert to Exception

Perfect for API boundaries:

```python
from fastapi import HTTPException

result = get_user(user_id)
user = result.unwrap_or_raise(lambda e: HTTPException(404, e))
```

### With Custom Message

```python
Ok(42).expect("should have value")       # 42
Err("oops").expect("should have value")  # Raises UnwrapError("should have value")
```

## Transformation Methods

### Transform Ok Value

```python
Ok(5).map(lambda x: x * 2)      # Ok(10)
Err("oops").map(lambda x: x * 2) # Err("oops") - unchanged
```

### Transform Err Value

```python
Ok(5).map_err(str.upper)         # Ok(5) - unchanged
Err("oops").map_err(str.upper)   # Err("OOPS")
```

### Chain Result-Returning Functions

Also known as "flatMap" or "bind" in functional programming:

```python
def validate_positive(n: int) -> Result[int, str]:
    return Ok(n) if n > 0 else Err("must be positive")

Ok(5).and_then(validate_positive)   # Ok(5)
Ok(-5).and_then(validate_positive)  # Err("must be positive")
Err("oops").and_then(validate_positive)  # Err("oops") - short-circuits
```

### Recover from Errors

```python
def try_backup(e: str) -> Result[int, str]:
    return Ok(0)  # fallback value

Err("oops").or_else(try_backup)  # Ok(0)
Ok(5).or_else(try_backup)        # Ok(5) - unchanged
```

## Inspection Methods

For side effects without changing the Result:

### Inspect `Ok` Value

```python
result = (
    Ok(42)
    .tee(lambda x: print(f"Got: {x}"))  # Prints "Got: 42"
    .map(lambda x: x * 2)
)
# result is Ok(84)
```

### Inspect `Err` Value

```python
result = (
    Err("oops")
    .inspect_err(lambda e: logger.error(f"Error: {e}"))
    .or_else(recover)
)
```

## Combining Results

### Combine Two Results

```python
Ok(1).zip(Ok(2))      # Ok((1, 2))
Ok(1).zip(Err("e"))   # Err("e")
Err("e").zip(Ok(2))   # Err("e")
```

### Combine with Function

```python
Ok(10).zip_with(Ok(3), lambda a, b: a + b)  # Ok(13)
```

### Unwrap Nested Results

```python
Ok(Ok(42)).flatten()  # Ok(42)
Ok(Err("e")).flatten() # Err("e")
Err("e").flatten()    # Err("e")
```

### Keep `Ok` If Predicate Passes

```python
Ok(42).filter(lambda x: x > 0, "must be positive")  # Ok(42)
Ok(-5).filter(lambda x: x > 0, "must be positive")  # Err("must be positive")
```

## Conversion Methods

### Convert to `Option`

```python
Ok(42).ok()     # Some(42)
Err("e").ok()   # NOTHING
```

### Convert Error to `Option`

```python
Ok(42).err()    # NOTHING
Err("e").err()  # Some("e")
```

### Convert to Tuple

```python
Ok(42).split()    # (42, None)
Err("e").split()  # (None, "e")
```

## Context and Error Chaining

### Add Context to Errors

```python
result = (
    parse_config("config.json")
    .context("loading configuration")
)
# If parse_config returns Err("file not found")
# Result is Err(ChainedError("loading configuration", "file not found"))
```

Chain multiple contexts:

```python
result = (
    read_file(path)
    .context("reading data file")
    .and_then(parse_json)
    .context("parsing JSON")
    .and_then(validate_schema)
    .context("validating schema")
)
# Error: "validating schema: parsing JSON: reading data file: ..."
```

## Async Methods

All transformation methods have async variants:

```python
async def fetch_user(id: int) -> User:
    ...

result = await Ok(42).map_async(fetch_user)  # Ok(User(...))
```

Available async methods:

- `map_async(fn)` - Transform with async function
- `map_err_async(fn)` - Transform error with async function
- `and_then_async(fn)` - Chain async Result-returning function
- `or_else_async(fn)` - Recover with async function
- `tee_async(fn)` / `inspect_async(fn)` - Async side effect on Ok
- `inspect_err_async(fn)` - Async side effect on Err

## Batch Operations

### Collect Results

Convert a list of Results into a Result of a list:

```python
from unwrappy import Ok, Err, sequence_results

results = [Ok(1), Ok(2), Ok(3)]
combined = sequence_results(results)  # Ok([1, 2, 3])

results = [Ok(1), Err("e"), Ok(3)]
combined = sequence_results(results)  # Err("e") - fails fast
```

### Map and Collect

Map a function over items and collect Results:

```python
from unwrappy import traverse_results

def parse_int(s: str) -> Result[int, str]:
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"invalid: {s}")

items = ["1", "2", "3"]
result = traverse_results(items, parse_int)  # Ok([1, 2, 3])

items = ["1", "x", "3"]
result = traverse_results(items, parse_int)  # Err("invalid: x")
```

## Best Practices

### 1. Use Structured Errors

Instead of string errors, use dataclasses or enums:

```python
from dataclasses import dataclass
from enum import Enum

class ErrorKind(Enum):
    NOT_FOUND = "not_found"
    VALIDATION = "validation"
    PERMISSION = "permission"

@dataclass
class AppError:
    kind: ErrorKind
    message: str
    details: dict | None = None

def get_user(id: int) -> Result[User, AppError]:
    if not exists(id):
        return Err(AppError(ErrorKind.NOT_FOUND, f"User {id} not found"))
    ...
```

### 2. Chain Operations

Prefer chaining over nested conditionals:

```python
# Instead of this:
result = parse(data)
if result.is_ok():
    result = validate(result.unwrap())
    if result.is_ok():
        result = transform(result.unwrap())

# Do this:
result = (
    parse(data)
    .and_then(validate)
    .map(transform)
)
```

### 3. Use Pattern Matching at Boundaries

Handle Results explicitly at API/UI boundaries:

```python
@app.get("/users/{id}")
def get_user_endpoint(id: int):
    match user_service.get_user(id):
        case Ok(user):
            return user.to_dict()
        case Err(AppError(kind=ErrorKind.NOT_FOUND)):
            raise HTTPException(404, "User not found")
        case Err(error):
            raise HTTPException(500, error.message)
```

### 4. Use `tee()` for Logging

```python
result = (
    fetch_data(url)
    .tee(lambda d: logger.info(f"Fetched {len(d)} bytes"))
    .and_then(parse)
    .inspect_err(lambda e: logger.error(f"Parse failed: {e}"))
)
```
