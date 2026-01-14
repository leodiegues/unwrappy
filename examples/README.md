# unwrappy Examples

Practical examples demonstrating Result and Option patterns in real-world scenarios.

## Running Examples

Run any example from the repository root:

```bash
uv run --script --with-editable . examples/web_api.py
```

The `--with-editable .` flag includes the local unwrappy package. Each example is a standalone [UV script](https://docs.astral.sh/uv/guides/scripts/) with inline dependencies - once unwrappy is published to PyPI, they'll work with just `uv run examples/web_api.py`.

## Examples

| File | Description |
|------|-------------|
| [web_api.py](./web_api.py) | FastAPI-style handlers, HTTP error mapping, request validation |
| [data_processing.py](./data_processing.py) | CSV/JSON parsing, transformations, batch operations |
| [database.py](./database.py) | Option for nullable lookups, repository pattern |
| [error_handling.py](./error_handling.py) | Context chaining, recovery patterns, before/after comparison |
| [async_patterns.py](./async_patterns.py) | LazyResult/LazyOption, async service composition |

## Key Patterns

### Result for Operations That Can Fail

```python
from unwrappy import Result, Ok, Err

def divide(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Err("division by zero")
    return Ok(a / b)

# Chain operations safely
result = divide(10, 2).map(lambda x: x * 2)  # Ok(10.0)
```

### Option for Values That May Not Exist

```python
from unwrappy import Option, Some, NOTHING, from_nullable

def find_user(user_id: int) -> Option[User]:
    user = db.get(user_id)  # Returns User | None
    return from_nullable(user)

# Chain with defaults
email = find_user(123).map(lambda u: u.email).unwrap_or("unknown")
```

### Error Context Chaining

```python
result = (
    parse_config(path)
    .context("loading configuration")
    .and_then(validate)
    .context("validating configuration")
)
# Error: "validating configuration: loading configuration: file not found"
```

### Type Guard Functions for Early Returns

Python's type system doesn't narrow types based on method return values. When using early returns, the `.is_err()` method requires `# type: ignore` comments:

```python
def process(user_id: int) -> Result[Profile, str]:
    user_result = fetch_user(user_id)  # Result[User, str]
    if user_result.is_err():
        return user_result  # type: ignore  <- Type checker complains

    return Ok(Profile(user_result.unwrap()))
```

Use the standalone type guard functions `is_ok`, `is_err`, `is_some`, and `is_nothing` instead:

```python
from unwrappy import Result, Ok, is_err

def process(user_id: int) -> Result[Profile, str]:
    user_result = fetch_user(user_id)  # Result[User, str]
    if is_err(user_result):
        return user_result  # No type: ignore needed!

    return Ok(Profile(user_result.unwrap()))
```

These functions use [`TypeIs`](https://docs.python.org/3/library/typing.html#typing.TypeIs) to enable proper type narrowing. This pattern is also used by [rustedpy/result](https://github.com/rustedpy/result).

**When to use which:**
- `.is_ok()` / `.is_err()` - When you don't need type narrowing (e.g., just checking status)
- `is_ok()` / `is_err()` - When returning early or assigning to variables with different Ok types
