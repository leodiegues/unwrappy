# Option API Reference

API documentation for the Option type and related classes.

## Type Alias

```python
Option[T] = Some[T] | Nothing
```

A type representing an optional value: either `Some[T]` (present) or `Nothing` (absent).

---

## Some

::: unwrappy.Some
    options:
      show_source: false
      members:
        - __init__
        - is_some
        - is_nothing
        - map
        - map_async
        - map_or
        - map_or_else
        - and_then
        - and_then_async
        - or_else
        - or_else_async
        - filter
        - filter_async
        - unwrap
        - unwrap_or
        - unwrap_or_else
        - unwrap_or_raise
        - expect
        - tee
        - inspect
        - tee_async
        - inspect_async
        - inspect_nothing
        - inspect_nothing_async
        - ok_or
        - ok_or_else
        - flatten
        - zip
        - zip_with
        - xor
        - to_tuple

---

## Nothing (NOTHING)

The `Nothing` type represents the absence of a value. `NOTHING` is the singleton instance.

```python
from unwrappy import NOTHING, Option

absent: Option[int] = NOTHING
```

### Methods

All methods on `Nothing` return appropriate "empty" values:

| Method | Return Value |
|--------|--------------|
| `is_some()` | `False` |
| `is_nothing()` | `True` |
| `map(fn)` | `NOTHING` |
| `and_then(fn)` | `NOTHING` |
| `or_else(fn)` | Result of `fn()` |
| `filter(pred)` | `NOTHING` |
| `unwrap()` | Raises `UnwrapError` |
| `unwrap_or(default)` | `default` |
| `unwrap_or_else(fn)` | Result of `fn()` |
| `ok_or(err)` | `Err(err)` |
| `flatten()` | `NOTHING` |
| `zip(other)` | `NOTHING` |
| `xor(other)` | `other` if `other` is Some, else `NOTHING` |
| `to_tuple()` | `()` |

---

## LazyOption

::: unwrappy.LazyOption
    options:
      show_source: false
      members:
        - from_option
        - from_awaitable
        - some
        - nothing
        - map
        - and_then
        - or_else
        - filter
        - tee
        - inspect
        - inspect_nothing
        - flatten
        - collect

---

## Type Guards

### is_some

::: unwrappy.is_some
    options:
      show_source: false

### is_nothing

::: unwrappy.is_nothing
    options:
      show_source: false

---

## Utility Functions

### from_nullable

::: unwrappy.from_nullable
    options:
      show_source: false

### sequence_options

::: unwrappy.sequence_options
    options:
      show_source: false

### traverse_options

::: unwrappy.traverse_options
    options:
      show_source: false
