---
hide:
  - navigation
---

# unwrappy

**Rust-inspired `Result` and `Option` types for Python**

Safe, expressive error handling with errors as values.

---

<div class="grid cards" markdown>

-   :material-check-circle:{ .lg .middle } **Explicit Error Handling**

    ---

    No hidden exceptions. Errors are values that must be handled, making your code's error paths visible and type-checkable.

-   :material-shield-check:{ .lg .middle } **Type Safe**

    ---

    Full generic type support with proper inference. Works with pyright, mypy, and ty out of the box.

-   :material-function:{ .lg .middle } **Functional Composition**

    ---

    Rich combinator API (`map`, `and_then`, `or_else`, etc.) for elegant transformation chains.

-   :material-lightning-bolt:{ .lg .middle } **Async First**

    ---

    `LazyResult` and `LazyOption` for clean async operation chaining without nested awaits.

</div>

## Quick Example

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

## Installation

```bash
pip install unwrappy
```

Or with uv:

```bash
uv add unwrappy
```

## Why unwrappy?

Python's exception-based error handling has fundamental issues for complex applications:

| Problem | With Exceptions | With unwrappy |
|---------|-----------------|---------------|
| **Hidden control flow** | Exceptions can be raised anywhere and caught anywhere | Errors are explicit values in function signatures |
| **Unclear contracts** | Function signatures don't declare what exceptions they raise | Return types show exactly what can fail |
| **Silent failures** | Forgotten exception handling leads to runtime crashes | Type checker enforces handling |

unwrappy provides `Result[T, E]` and `Option[T]` types that make errors **explicit values** in your code.

## Core Types

### Result[T, E]

Represents either success (`Ok`) or failure (`Err`):

```python
from unwrappy import Ok, Err, Result

def parse_int(s: str) -> Result[int, str]:
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"invalid number: {s}")

result = parse_int("42")
result.unwrap()      # 42
result.is_ok()       # True
```

[Learn more about Result :material-arrow-right:](guide/result.md){ .md-button }

### Option[T]

Represents an optional value (`Some` or `Nothing`):

```python
from unwrappy import Some, NOTHING, Option, from_nullable

def find_user(user_id: int) -> Option[User]:
    user = db.get(user_id)  # Returns User | None
    return from_nullable(user)

email = find_user(123).map(lambda u: u.email).unwrap_or("unknown")
```

[Learn more about Option :material-arrow-right:](guide/option.md){ .md-button }

### LazyResult & LazyOption

Deferred execution for clean async chaining:

```python
from unwrappy import LazyResult

async def fetch_user(id: int) -> Result[User, str]: ...
async def fetch_profile(user: User) -> Result[Profile, str]: ...

# Build pipeline, execute once - no nested awaits!
result = await (
    LazyResult.from_awaitable(fetch_user(42))
    .and_then(fetch_profile)
    .map(lambda p: p.name)
    .collect()
)
```

[Learn more about Lazy Evaluation :material-arrow-right:](guide/lazy-evaluation.md){ .md-button }

## Design Philosophy

unwrappy is designed for **practical use** in real Python codebases:

- **Zero dependencies** - Just Python stdlib
- **Incremental adoption** - Use in a single module or throughout your codebase
- **Framework friendly** - Works alongside FastAPI, Django, Flask, etc.
- **No magic** - No decorators, no metaclasses, no import hooks

[Read the Architecture docs :material-arrow-right:](architecture.md){ .md-button .md-button--primary }

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Installation, basic usage, and your first Result-based function.

    [:octicons-arrow-right-24: Get started](getting-started.md)

-   :material-book-open-variant:{ .lg .middle } **Guide**

    ---

    Deep dive into Result, Option, and async patterns.

    [:octicons-arrow-right-24: Read the guide](guide/result.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation with all methods and functions.

    [:octicons-arrow-right-24: API docs](api/result.md)

-   :material-code-tags:{ .lg .middle } **Examples**

    ---

    Real-world patterns and code examples.

    [:octicons-arrow-right-24: View examples](examples.md)

</div>
