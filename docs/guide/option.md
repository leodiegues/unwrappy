# Option Type

The `Option[T]` type represents a value that may or may not be present: either `Some(value)` or `Nothing`.

## Overview

```python
from unwrappy import Some, NOTHING, Option

# Value is present
some: Option[int] = Some(42)

# Value is absent
nothing: Option[int] = NOTHING
```

Option is a **union type** (type alias):

```python
Option[T] = Some[T] | Nothing
```

Where `Nothing` is a singleton (like Python's `None`).

## Creating Options

### Present Variant

```python
from unwrappy import Some

opt = Some(42)              # Some[int]
opt = Some("hello")         # Some[str]
opt = Some([1, 2, 3])       # Some[list[int]]
```

### Absent Variant

```python
from unwrappy import NOTHING, Option

# NOTHING is a singleton
opt: Option[int] = NOTHING

# All NOTHING values are the same instance
assert NOTHING is NOTHING  # True
```

!!! note "NOTHING vs Nothing"
    - `NOTHING` is the singleton value (use in code)
    - `Nothing` is the type alias (use in type hints): `def foo() -> Option[int]:` can return `NOTHING`

### Convert from Python's None

The most common way to create Options from existing code:

```python
from unwrappy import from_nullable

# Convert nullable values
opt = from_nullable(None)        # NOTHING
opt = from_nullable(42)          # Some(42)
opt = from_nullable("")          # Some("") - empty string is not None!
opt = from_nullable([])          # Some([]) - empty list is not None!

# Common pattern with dict.get()
config = {"debug": "true"}
opt = from_nullable(config.get("debug"))    # Some("true")
opt = from_nullable(config.get("missing"))  # NOTHING
```

## Option vs typing.Optional

Python's `Optional[T]` is just `T | None` - it doesn't distinguish between "value is absent" and "value is explicitly None".

Option makes this explicit:

```python
# typing.Optional - ambiguous
def get_setting() -> str | None:
    return None  # Is this "no setting" or "setting is null"?

# unwrappy.Option - clear
def get_setting() -> Option[str]:
    return Some("value")  # Setting exists
    return NOTHING        # No setting
```

### Three-State Logic with Option[T | None]

For PATCH-style updates where you need to distinguish between "don't update", "set to null", and "set to value":

```python
from dataclasses import dataclass, field
from unwrappy import Option, Some, NOTHING

@dataclass
class UserUpdate:
    # NOTHING = don't update this field
    # Some(None) = set field to null
    # Some(value) = set field to value
    name: Option[str | None] = NOTHING
    email: Option[str | None] = NOTHING

def apply_update(user: User, update: UserUpdate) -> User:
    match update.name:
        case Some(None):
            user.name = None  # Explicitly set to null
        case Some(name):
            user.name = name  # Set to new value
        case _:
            pass  # NOTHING - don't change

    return user
```

## Checking Variants

### Methods

```python
some = Some(42)
nothing = NOTHING

some.is_some()      # True
some.is_nothing()   # False

nothing.is_some()   # False
nothing.is_nothing() # True
```

### Type Guard Functions

For proper type narrowing:

```python
from unwrappy import Option, Some, NOTHING, is_some, is_nothing

def process(opt: Option[int]) -> int:
    if is_nothing(opt):
        return 0

    # Type checker knows opt is Some[int] here
    return opt.unwrap() * 2
```

## Pattern Matching

The recommended way to handle Options (Python 3.10+):

```python
from unwrappy import Some, NOTHING, Option

def describe(opt: Option[int]) -> str:
    match opt:
        case Some(value):
            return f"Got: {value}"
        case _:  # NOTHING
            return "Nothing here"
```

!!! tip "Matching NOTHING"
    Use `case _:` or `case NOTHING` (imported) to match the Nothing variant. Using `case Nothing:` without import won't work as expected.

## Extracting Values

### Get Value or Raise

```python
Some(42).unwrap()   # 42
NOTHING.unwrap()    # Raises UnwrapError
```

### With Default

```python
Some(42).unwrap_or(0)   # 42
NOTHING.unwrap_or(0)    # 0
```

### With Computed Default

```python
Some(42).unwrap_or_else(lambda: expensive_default())   # 42 (lambda not called)
NOTHING.unwrap_or_else(lambda: expensive_default())    # calls expensive_default()
```

### Convert to Exception

```python
Some(42).unwrap_or_raise(ValueError("missing"))   # 42
NOTHING.unwrap_or_raise(ValueError("missing"))    # Raises ValueError
```

### With Custom Message

```python
Some(42).expect("value required")   # 42
NOTHING.expect("value required")    # Raises UnwrapError("value required")
```

## Transformation Methods

### Transform Some Value

```python
Some(5).map(lambda x: x * 2)   # Some(10)
NOTHING.map(lambda x: x * 2)   # NOTHING
```

### Transform or Return Default

```python
Some(5).map_or(0, lambda x: x * 2)   # 10
NOTHING.map_or(0, lambda x: x * 2)   # 0
```

### Transform or Compute Default

```python
Some(5).map_or_else(lambda: 0, lambda x: x * 2)   # 10
NOTHING.map_or_else(lambda: 0, lambda x: x * 2)   # 0
```

### Chain Option-Returning Functions

```python
def parse_port(s: str) -> Option[int]:
    try:
        port = int(s)
        return Some(port) if 1 <= port <= 65535 else NOTHING
    except ValueError:
        return NOTHING

Some("8080").and_then(parse_port)    # Some(8080)
Some("invalid").and_then(parse_port) # NOTHING
NOTHING.and_then(parse_port)         # NOTHING
```

### Provide Alternative

```python
def get_from_env() -> Option[str]:
    return from_nullable(os.environ.get("CONFIG"))

def get_from_file() -> Option[str]:
    return Some("default") if path.exists() else NOTHING

config = get_from_env().or_else(get_from_file)
```

### Keep Value If Predicate Passes

```python
Some(42).filter(lambda x: x > 0)    # Some(42)
Some(-5).filter(lambda x: x > 0)    # NOTHING
NOTHING.filter(lambda x: x > 0)     # NOTHING
```

## Inspection Methods

### Side Effect on Some

```python
result = (
    Some(42)
    .tee(lambda x: print(f"Got: {x}"))  # Prints "Got: 42"
    .map(lambda x: x * 2)
)
# result is Some(84)
```

### Side Effect on Nothing

```python
result = (
    NOTHING
    .inspect_nothing(lambda: logger.warning("No value found"))
    .or_else(get_default)
)
```

## Combining Options

### Combine Two Options

```python
Some(1).zip(Some(2))    # Some((1, 2))
Some(1).zip(NOTHING)    # NOTHING
NOTHING.zip(Some(2))    # NOTHING
```

### Combine with Function

```python
Some(10).zip_with(Some(3), lambda a, b: a + b)  # Some(13)
```

### Unwrap Nested Options

```python
Some(Some(42)).flatten()  # Some(42)
Some(NOTHING).flatten()   # NOTHING
NOTHING.flatten()         # NOTHING
```

### Exactly One Must Be Some

```python
Some(1).xor(NOTHING)   # Some(1)
NOTHING.xor(Some(2))   # Some(2)
Some(1).xor(Some(2))   # NOTHING (both are Some)
NOTHING.xor(NOTHING)   # NOTHING (neither is Some)
```

## Conversion Methods

### Convert to Result

```python
from unwrappy import Some, NOTHING

Some(42).ok_or("missing")   # Ok(42)
NOTHING.ok_or("missing")    # Err("missing")
```

### Convert to Result with Computed Error

```python
Some(42).ok_or_else(lambda: "missing")   # Ok(42)
NOTHING.ok_or_else(lambda: "missing")    # Err("missing")
```

### Convert to Single-Element Tuple or Empty

```python
Some(42).to_tuple()  # (42,)
NOTHING.to_tuple()   # ()
```

Useful for unpacking:

```python
for value in Some(42).to_tuple():
    print(value)  # Prints 42

for value in NOTHING.to_tuple():
    print(value)  # Nothing printed
```

## Async Methods

All transformation methods have async variants:

```python
async def fetch_details(id: int) -> str:
    ...

opt = await Some(42).map_async(fetch_details)  # Some("details...")
```

Available async methods:

- `map_async(fn)` - Transform with async function
- `and_then_async(fn)` - Chain async Option-returning function
- `or_else_async(fn)` - Provide async alternative
- `tee_async(fn)` / `inspect_async(fn)` - Async side effect on Some
- `inspect_nothing_async(fn)` - Async side effect on Nothing

## Batch Operations

### Collect Options

Convert a list of Options into an Option of a list:

```python
from unwrappy import Some, NOTHING, sequence_options

options = [Some(1), Some(2), Some(3)]
combined = sequence_options(options)  # Some([1, 2, 3])

options = [Some(1), NOTHING, Some(3)]
combined = sequence_options(options)  # NOTHING - fails fast
```

### Map and Collect

Map a function over items and collect Options:

```python
from unwrappy import traverse_options, from_nullable

items = [1, 2, 3]
result = traverse_options(items, lambda x: Some(x * 2))  # Some([2, 4, 6])

# With nullable values
items: list[int | None] = [1, 2, 3]
result = traverse_options(items, from_nullable)  # Some([1, 2, 3])

items: list[int | None] = [1, None, 3]
result = traverse_options(items, from_nullable)  # NOTHING
```

## Best Practices

### 1. Use `from_nullable()` at Boundaries

Convert nullable values to Option at the boundary of your domain logic:

```python
def get_user_email(user_id: int) -> Option[str]:
    # External API returns str | None
    email = external_api.get_email(user_id)
    return from_nullable(email)
```

### 2. Chain Operations

Prefer chaining over nested conditionals:

```python
# Instead of this:
email = get_email()
if email is not None:
    domain = email.split("@")[1] if "@" in email else None
    if domain is not None:
        result = domain.lower()
    else:
        result = "unknown"
else:
    result = "unknown"

# Do this:
result = (
    from_nullable(get_email())
    .filter(lambda e: "@" in e)
    .map(lambda e: e.split("@")[1])
    .map(str.lower)
    .unwrap_or("unknown")
)
```

### 3. Convert to Result When Error Context Matters

When you need to know *why* a value is missing:

```python
def get_config(key: str) -> Option[str]:
    return from_nullable(config.get(key))

def get_required_config(key: str) -> Result[str, str]:
    return get_config(key).ok_or(f"Missing required config: {key}")

# Now you have error context
match get_required_config("API_KEY"):
    case Ok(key):
        use_key(key)
    case Err(error):
        print(error)  # "Missing required config: API_KEY"
```

### 4. Use `filter()` for Validation

```python
def parse_port(s: str) -> Option[int]:
    return (
        from_nullable(s)
        .and_then(lambda s: Some(int(s)) if s.isdigit() else NOTHING)
        .filter(lambda p: 1 <= p <= 65535)
    )
```
