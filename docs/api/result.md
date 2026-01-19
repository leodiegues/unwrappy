# Result API Reference

API documentation for the Result type and related classes.

## Type Alias

```python
Result[T, E] = Ok[T] | Err[E]
```

A type representing either success (`Ok[T]`) or failure (`Err[E]`).

---

## Ok

::: unwrappy.Ok
    options:
      show_source: false
      members:
        - __init__
        - is_ok
        - is_err
        - ok
        - err
        - map
        - map_async
        - map_err
        - map_err_async
        - and_then
        - and_then_async
        - or_else
        - or_else_async
        - unwrap
        - unwrap_or
        - unwrap_or_else
        - unwrap_or_raise
        - unwrap_err
        - expect
        - tee
        - inspect
        - tee_async
        - inspect_async
        - inspect_err
        - inspect_err_async
        - flatten
        - split
        - filter
        - zip
        - zip_with
        - context

---

## Err

::: unwrappy.Err
    options:
      show_source: false
      members:
        - __init__
        - is_ok
        - is_err
        - ok
        - err
        - map
        - map_async
        - map_err
        - map_err_async
        - and_then
        - and_then_async
        - or_else
        - or_else_async
        - unwrap
        - unwrap_or
        - unwrap_or_else
        - unwrap_or_raise
        - unwrap_err
        - expect
        - tee
        - inspect
        - tee_async
        - inspect_async
        - inspect_err
        - inspect_err_async
        - flatten
        - split
        - filter
        - zip
        - zip_with
        - context

---

## LazyResult

::: unwrappy.LazyResult
    options:
      show_source: false
      members:
        - from_result
        - from_awaitable
        - ok
        - err
        - map
        - map_err
        - and_then
        - or_else
        - tee
        - inspect
        - inspect_err
        - flatten
        - collect

---

## Type Guards

### is_ok

::: unwrappy.is_ok
    options:
      show_source: false

### is_err

::: unwrappy.is_err
    options:
      show_source: false

---

## Utility Functions

### sequence_results

::: unwrappy.sequence_results
    options:
      show_source: false

### traverse_results

::: unwrappy.traverse_results
    options:
      show_source: false

---

## Exceptions

### UnwrapError

::: unwrappy.UnwrapError
    options:
      show_source: false

### ChainedError

::: unwrappy.ChainedError
    options:
      show_source: false
