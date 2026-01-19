# API Reference

Complete API documentation for unwrappy, auto-generated from source code docstrings.

## Modules

<div class="grid cards" markdown>

-   :material-check-circle:{ .lg .middle } **Result**

    ---

    The `Result[T, E]` type and related classes for error handling.

    - `Ok[T]` - Success variant
    - `Err[E]` - Error variant
    - `LazyResult[T, E]` - Deferred execution
    - Utility functions

    [:octicons-arrow-right-24: Result API](result.md)

-   :material-help-circle:{ .lg .middle } **Option**

    ---

    The `Option[T]` type and related classes for optional values.

    - `Some[T]` - Present variant
    - `Nothing` - Absent variant
    - `LazyOption[T]` - Deferred execution
    - Utility functions

    [:octicons-arrow-right-24: Option API](option.md)

</div>

## Quick Reference

### Result Types

| Type | Description |
|------|-------------|
| `Result[T, E]` | Type alias for `Ok[T] \| Err[E]` |
| `Ok[T]` | Success variant containing a value |
| `Err[E]` | Error variant containing an error |
| `LazyResult[T, E]` | Deferred Result computation |

### Option Types

| Type | Description |
|------|-------------|
| `Option[T]` | Type alias for `Some[T] \| Nothing` |
| `Some[T]` | Present variant containing a value |
| `Nothing` | Absent variant (singleton type) |
| `NOTHING` | The Nothing singleton instance |
| `LazyOption[T]` | Deferred Option computation |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `UnwrapError` | Raised when unwrapping fails |
| `ChainedError` | Error with context chain |

### Utility Functions

| Function | Description |
|----------|-------------|
| `from_nullable(value)` | Convert `T \| None` to `Option[T]` |
| `sequence_results(results)` | Collect `list[Result]` to `Result[list]` |
| `traverse_results(items, fn)` | Map and collect Results |
| `sequence_options(options)` | Collect `list[Option]` to `Option[list]` |
| `traverse_options(items, fn)` | Map and collect Options |
| `is_ok(result)` | Type guard for Ok |
| `is_err(result)` | Type guard for Err |
| `is_some(option)` | Type guard for Some |
| `is_nothing(option)` | Type guard for Nothing |

### Serialization

| Function/Class | Description |
|----------------|-------------|
| `dumps(obj)` | Serialize to JSON string |
| `loads(s)` | Deserialize from JSON string |
| `ResultEncoder` | JSON encoder class |
| `result_decoder` | JSON decoder hook |
