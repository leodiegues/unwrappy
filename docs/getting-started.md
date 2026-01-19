# Getting Started

This guide will help you get up and running with unwrappy in minutes.

## Installation

=== "pip"

    ```bash
    pip install unwrappy
    ```

=== "uv"

    ```bash
    uv add unwrappy
    ```

=== "poetry"

    ```bash
    poetry add unwrappy
    ```

## Requirements

- Python 3.10 or higher
- No external dependencies

## Basic Usage

### Your First Result

The `Result` type represents an operation that can succeed or fail:

```python
from unwrappy import Ok, Err, Result

def divide(a: float, b: float) -> Result[float, str]:
    """Divide two numbers, returning an error for division by zero."""
    if b == 0:
        return Err("cannot divide by zero")
    return Ok(a / b)
```

### Handling Results

There are several ways to handle a `Result`:

#### Pattern Matching (Recommended)

Python 3.10+ structural pattern matching is the most explicit way:

```python
match divide(10, 2):
    case Ok(value):
        print(f"Result: {value}")  # Result: 5.0
    case Err(error):
        print(f"Error: {error}")
```

#### Checking and Unwrapping

For simpler cases, check the variant and extract the value:

```python
result = divide(10, 2)

if result.is_ok():
    print(result.unwrap())  # 5.0
else:
    print(result.unwrap_err())  # Would print the error message
```

#### Safe Extraction with Defaults

When you want a fallback value:

```python
# With a default value
value = divide(10, 0).unwrap_or(0.0)  # 0.0

# With a computed default
value = divide(10, 0).unwrap_or_else(lambda e: float("inf"))  # inf
```

### Chaining Operations

The real power comes from chaining operations:

```python
def parse_int(s: str) -> Result[int, str]:
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"'{s}' is not a valid integer")

def validate_positive(n: int) -> Result[int, str]:
    if n <= 0:
        return Err("number must be positive")
    return Ok(n)

# Chain multiple operations
result = (
    parse_int("42")
    .and_then(validate_positive)
    .map(lambda x: x * 2)
)

print(result)  # Ok(84)
```

If any step fails, the chain short-circuits:

```python
result = (
    parse_int("not a number")  # This fails
    .and_then(validate_positive)  # Skipped
    .map(lambda x: x * 2)  # Skipped
)

print(result)  # Err("'not a number' is not a valid integer")
```

## Working with Optional Values

The `Option` type handles values that may or may not exist:

```python
from unwrappy import Some, NOTHING, Option, from_nullable

# Create Options manually
present: Option[int] = Some(42)
absent: Option[int] = NOTHING

# Convert from nullable Python values
def get_config_value(key: str) -> str | None:
    return {"debug": "true"}.get(key)

opt = from_nullable(get_config_value("debug"))  # Some("true")
opt = from_nullable(get_config_value("missing"))  # NOTHING
```

### Option Chaining

Chain operations on optional values:

```python
# Get a config value, parse it, and provide a default
debug_enabled = (
    from_nullable(get_config_value("debug"))
    .map(lambda s: s.lower() == "true")
    .unwrap_or(False)
)
```

## Type Safety

unwrappy is designed for type checkers. Your IDE will catch errors:

```python
from unwrappy import Ok, Err, Result

def get_user(id: int) -> Result[User, str]:
    ...

result = get_user(42)

# Type checker knows result could be Ok or Err
user = result.unwrap()  # Type checker warns: could raise UnwrapError!

# Safe pattern matching - type checker knows value is User
match result:
    case Ok(user):
        print(user.name)  # user is typed as User
    case Err(error):
        print(error)  # error is typed as str
```

## Integration with Existing Code

unwrappy is designed for gradual adoption. Use it alongside exceptions:

```python
from unwrappy import Ok, Err, Result

# Business logic uses Result
def validate_email(email: str) -> Result[str, str]:
    if "@" not in email:
        return Err("invalid email format")
    return Ok(email)

# API boundary converts to exceptions
@app.post("/users")
def create_user(email: str):
    match validate_email(email):
        case Ok(valid_email):
            return {"email": valid_email}
        case Err(error):
            raise HTTPException(400, error)
```

Or use `unwrap_or_raise` for cleaner conversion:

```python
@app.post("/users")
def create_user(email: str):
    valid_email = validate_email(email).unwrap_or_raise(
        lambda e: HTTPException(400, e)
    )
    return {"email": valid_email}
```

## Next Steps

Now that you understand the basics:

- [**Result Guide**](guide/result.md) - Deep dive into Result methods and patterns
- [**Option Guide**](guide/option.md) - Working with optional values
- [**Lazy Evaluation**](guide/lazy-evaluation.md) - Async patterns with LazyResult
- [**Examples**](examples.md) - Real-world code examples
