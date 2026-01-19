# Examples

Practical examples demonstrating Result and Option patterns in real-world scenarios.

## Running Examples

The examples are available in the [examples/](https://github.com/leodiegues/unwrappy/tree/main/examples) directory. Run any example from the repository root:

```bash
uv run --script --with-editable . examples/web_api.py
```

## Example Files

| File | Description |
|------|-------------|
| [web_api.py](https://github.com/leodiegues/unwrappy/blob/main/examples/web_api.py) | FastAPI-style handlers, HTTP error mapping, request validation |
| [data_processing.py](https://github.com/leodiegues/unwrappy/blob/main/examples/data_processing.py) | CSV/JSON parsing, transformations, batch operations |
| [database.py](https://github.com/leodiegues/unwrappy/blob/main/examples/database.py) | Option for nullable lookups, repository pattern |
| [error_handling.py](https://github.com/leodiegues/unwrappy/blob/main/examples/error_handling.py) | Context chaining, recovery patterns, before/after comparison |
| [async_patterns.py](https://github.com/leodiegues/unwrappy/blob/main/examples/async_patterns.py) | LazyResult/LazyOption, async service composition |

---

## Common Patterns

### Basic Error Handling

Transform a function that raises exceptions into one that returns Result:

```python
from unwrappy import Ok, Err, Result

def parse_int(s: str) -> Result[int, str]:
    """Parse a string to int, returning Result instead of raising."""
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"'{s}' is not a valid integer")

# Usage
result = parse_int("42")   # Ok(42)
result = parse_int("abc")  # Err("'abc' is not a valid integer")
```

### Chaining Validations

Chain multiple validation steps, short-circuiting on first error:

```python
from unwrappy import Ok, Err, Result

def validate_username(name: str) -> Result[str, str]:
    if len(name) < 3:
        return Err("username must be at least 3 characters")
    if not name.isalnum():
        return Err("username must be alphanumeric")
    return Ok(name)

def validate_email(email: str) -> Result[str, str]:
    if "@" not in email:
        return Err("invalid email format")
    return Ok(email)

def validate_age(age: int) -> Result[int, str]:
    if age < 18:
        return Err("must be 18 or older")
    return Ok(age)

# Chain validations
def validate_user(name: str, email: str, age: int) -> Result[dict, str]:
    return (
        validate_username(name)
        .and_then(lambda n: validate_email(email).map(lambda e: (n, e)))
        .and_then(lambda t: validate_age(age).map(lambda a: {
            "username": t[0],
            "email": t[1],
            "age": a
        }))
    )

# Usage
result = validate_user("alice", "alice@example.com", 25)  # Ok({...})
result = validate_user("ab", "alice@example.com", 25)     # Err("username must be...")
```

### Error Recovery

Provide fallback values or alternative operations:

```python
from unwrappy import Ok, Err, Result

def get_config_from_env(key: str) -> Result[str, str]:
    import os
    value = os.environ.get(key)
    if value is None:
        return Err(f"environment variable {key} not set")
    return Ok(value)

def get_config_from_file(key: str) -> Result[str, str]:
    # Try to read from config file
    config = {"PORT": "8080", "HOST": "localhost"}
    if key in config:
        return Ok(config[key])
    return Err(f"key {key} not in config file")

# Try env first, fall back to file
port = (
    get_config_from_env("PORT")
    .or_else(lambda _: get_config_from_file("PORT"))
    .unwrap_or("3000")
)
```

### Context Chaining

Add context to errors for better debugging:

```python
from unwrappy import Ok, Err, Result

def read_file(path: str) -> Result[str, str]:
    try:
        with open(path) as f:
            return Ok(f.read())
    except FileNotFoundError:
        return Err(f"file not found: {path}")

def parse_json(content: str) -> Result[dict, str]:
    import json
    try:
        return Ok(json.loads(content))
    except json.JSONDecodeError as e:
        return Err(f"invalid JSON: {e}")

def load_config(path: str) -> Result[dict, str]:
    return (
        read_file(path)
        .context("reading config file")
        .and_then(parse_json)
        .context("parsing config")
    )

# Error: "parsing config: reading config file: file not found: config.json"
```

### Web API Pattern

Handle Results at API boundaries:

```python
from unwrappy import Ok, Err, Result, is_err

# Domain service returns Result
def get_user(user_id: int) -> Result[dict, str]:
    users = {1: {"id": 1, "name": "Alice"}}
    if user_id not in users:
        return Err(f"user {user_id} not found")
    return Ok(users[user_id])

def update_user(user_id: int, data: dict) -> Result[dict, str]:
    user_result = get_user(user_id)
    if is_err(user_result):
        return user_result

    user = user_result.unwrap()
    user.update(data)
    return Ok(user)

# API handler converts to exceptions
def api_get_user(user_id: int):
    """FastAPI-style handler."""
    match get_user(user_id):
        case Ok(user):
            return {"data": user}
        case Err(error):
            # raise HTTPException(404, error)
            return {"error": error, "status": 404}

# Or using unwrap_or_raise
def api_get_user_v2(user_id: int):
    user = get_user(user_id).unwrap_or_raise(
        lambda e: Exception(e)  # Replace with HTTPException
    )
    return {"data": user}
```

### Optional Value Handling

Work with values that may not exist:

```python
from unwrappy import Some, NOTHING, Option, from_nullable

# Database-style lookup returning Option
def find_user_by_email(email: str) -> Option[dict]:
    users = {"alice@example.com": {"id": 1, "name": "Alice"}}
    return from_nullable(users.get(email))

# Chain operations on optional values
def get_user_display_name(email: str) -> str:
    return (
        find_user_by_email(email)
        .map(lambda u: u.get("display_name") or u["name"])
        .map(str.title)
        .unwrap_or("Unknown User")
    )

# Convert to Result when error context is needed
def require_user(email: str) -> Result[dict, str]:
    return find_user_by_email(email).ok_or(f"no user with email: {email}")
```

### Batch Processing

Process collections with error handling:

```python
from unwrappy import Ok, Err, Result, sequence_results, traverse_results

def parse_int(s: str) -> Result[int, str]:
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"invalid: {s}")

# Parse multiple values, fail on first error
inputs = ["1", "2", "3"]
result = traverse_results(inputs, parse_int)  # Ok([1, 2, 3])

inputs = ["1", "x", "3"]
result = traverse_results(inputs, parse_int)  # Err("invalid: x")

# Combine existing Results
results = [Ok(1), Ok(2), Ok(3)]
combined = sequence_results(results)  # Ok([1, 2, 3])
```

### Async Service Composition

Build async pipelines with LazyResult:

```python
from unwrappy import LazyResult, Ok, Err, Result

# Simulated async services
async def fetch_user(user_id: int) -> Result[dict, str]:
    if user_id <= 0:
        return Err("invalid user id")
    return Ok({"id": user_id, "name": "Alice"})

async def fetch_orders(user: dict) -> Result[list, str]:
    return Ok([{"id": 1, "total": 100}, {"id": 2, "total": 200}])

async def calculate_total(orders: list) -> int:
    return sum(o["total"] for o in orders)

# Build and execute pipeline
async def get_user_total(user_id: int) -> Result[int, str]:
    return await (
        LazyResult.from_awaitable(fetch_user(user_id))
        .and_then(fetch_orders)
        .map(calculate_total)  # Works with both sync and async!
        .tee(lambda total: print(f"Total: ${total}"))
        .collect()
    )

# Usage
# result = await get_user_total(42)  # Ok(300)
```

### Type Guard for Early Returns

Use type guards for proper type narrowing:

```python
from unwrappy import Ok, Err, Result, is_err, is_ok

def process_data(raw: str) -> Result[dict, str]:
    # Parse step
    parsed = parse_json(raw)
    if is_err(parsed):
        return parsed  # Type checker knows this is Err

    # Validate step
    validated = validate_schema(parsed.unwrap())
    if is_err(validated):
        return validated

    # Transform step
    data = validated.unwrap()
    return Ok({"processed": data, "timestamp": time.time()})
```

### Combining Option with Result

Convert between Option and Result as needed:

```python
from unwrappy import Some, NOTHING, Option, Ok, Err, Result, from_nullable

def find_config(key: str) -> Option[str]:
    """Returns Option - value may not exist."""
    config = {"api_key": "secret123"}
    return from_nullable(config.get(key))

def require_config(key: str) -> Result[str, str]:
    """Returns Result - missing config is an error."""
    return find_config(key).ok_or(f"missing required config: {key}")

def get_optional_config(key: str, default: str) -> str:
    """Returns value or default."""
    return find_config(key).unwrap_or(default)

# Usage
api_key = require_config("api_key")         # Ok("secret123")
missing = require_config("missing")         # Err("missing required config: missing")
timeout = get_optional_config("timeout", "30")  # "30"
```

### Logging and Side Effects

Use tee/inspect for debugging without breaking chains:

```python
import logging
from unwrappy import Ok, Err, Result

logger = logging.getLogger(__name__)

def fetch_and_process(url: str) -> Result[dict, str]:
    return (
        fetch_data(url)
        .tee(lambda d: logger.info(f"Fetched {len(d)} bytes from {url}"))
        .and_then(parse_json)
        .tee(lambda j: logger.debug(f"Parsed JSON: {j}"))
        .inspect_err(lambda e: logger.error(f"Processing failed: {e}"))
        .and_then(validate)
        .tee(lambda v: logger.info(f"Validation passed"))
    )
```

---

## See Also

- [Getting Started](getting-started.md) - Basic usage and concepts
- [Result Guide](guide/result.md) - Complete Result documentation
- [Option Guide](guide/option.md) - Complete Option documentation
- [Lazy Evaluation](guide/lazy-evaluation.md) - Async patterns
