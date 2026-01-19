# Guide

This guide provides comprehensive documentation for unwrappy's core types and patterns.

## Core Concepts

unwrappy brings Rust's approach to error handling to Python:

- **Errors as values** - Instead of throwing exceptions, functions return `Result` types that explicitly represent success or failure
- **Optional values** - Instead of `None`, use `Option` to make optionality explicit and chainable
- **Functional composition** - Chain operations with combinators like `map`, `and_then`, and `or_else`

## Type System

```
Result[T, E] = Ok[T] | Err[E]
  - Ok[T]   : Success variant containing a value of type T
  - Err[E]  : Error variant containing an error of type E

Option[T] = Some[T] | Nothing
  - Some[T] : Present variant containing a value of type T
  - Nothing : Absent variant (singleton)

LazyResult[T, E] : Deferred Result computation for async chains
LazyOption[T]    : Deferred Option computation for async chains
```

## Guide Sections

<div class="grid cards" markdown>

-   :material-check-circle:{ .lg .middle } **Result Type**

    ---

    The `Result[T, E]` type for operations that can fail. Learn about `Ok`, `Err`, and all the transformation methods.

    [:octicons-arrow-right-24: Result Guide](result.md)

-   :material-help-circle:{ .lg .middle } **Option Type**

    ---

    The `Option[T]` type for values that may not exist. Learn about `Some`, `Nothing`, and optional value handling.

    [:octicons-arrow-right-24: Option Guide](option.md)

-   :material-lightning-bolt:{ .lg .middle } **Lazy Evaluation**

    ---

    `LazyResult` and `LazyOption` for building async operation pipelines without nested awaits.

    [:octicons-arrow-right-24: Lazy Evaluation](lazy-evaluation.md)

-   :material-code-json:{ .lg .middle } **Serialization**

    ---

    JSON serialization support for task queues and distributed systems (Celery, Temporal, DBOS).

    [:octicons-arrow-right-24: Serialization](serialization.md)

</div>

## Quick Reference

### Result Methods

| Category | Methods |
|----------|---------|
| **Checking** | `is_ok()`, `is_err()` |
| **Transformation** | `map()`, `map_err()`, `and_then()`, `or_else()` |
| **Extraction** | `unwrap()`, `unwrap_or()`, `unwrap_or_else()`, `expect()` |
| **Inspection** | `tee()`, `inspect()`, `inspect_err()` |
| **Conversion** | `ok()`, `err()`, `flatten()`, `split()` |

### Option Methods

| Category | Methods |
|----------|---------|
| **Checking** | `is_some()`, `is_nothing()` |
| **Transformation** | `map()`, `and_then()`, `or_else()`, `filter()` |
| **Extraction** | `unwrap()`, `unwrap_or()`, `unwrap_or_else()`, `expect()` |
| **Inspection** | `tee()`, `inspect()`, `inspect_nothing()` |
| **Conversion** | `ok_or()`, `ok_or_else()`, `flatten()`, `to_tuple()` |

### Utility Functions

| Function | Description |
|----------|-------------|
| `from_nullable(value)` | Convert `T | None` to `Option[T]` |
| `sequence_results(results)` | Collect `list[Result]` into `Result[list]` |
| `traverse_results(items, fn)` | Map and collect Results |
| `sequence_options(options)` | Collect `list[Option]` into `Option[list]` |
| `traverse_options(items, fn)` | Map and collect Options |
