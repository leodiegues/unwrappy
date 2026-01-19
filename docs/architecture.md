# Architecture

This document explains the design decisions and architectural choices in unwrappy.

## Introduction

### What Problem Does unwrappy Solve?

Python's exception-based error handling has fundamental issues for complex applications:

1. **Hidden control flow**: Exceptions can be raised anywhere and caught anywhere, making it hard to trace error paths
2. **Unclear contracts**: Function signatures don't declare what exceptions they raise
3. **Overly broad catching**: `except Exception` can mask bugs like typos causing `NameError`
4. **Silent failures**: Forgotten exception handling leads to runtime crashes

unwrappy provides `Result[T, E]` and `Option[T]` types that make errors **explicit values** in your code. Instead of throwing exceptions that might be caught (or not), functions return `Ok(value)` or `Err(error)`—making error handling visible and type-checkable.

### Who Is This For?

unwrappy is designed for Python developers who:

- Want **explicit error handling** without hidden control flow
- Value **type safety** and use type checkers (pyright, mypy, ty)
- Come from **Rust, Go, or functional programming** backgrounds
- Build **business logic** where error paths matter as much as happy paths
- Need **async support** without callback hell

It's particularly useful in:

- API services where errors need to be translated to HTTP responses
- Data pipelines where partial failures need explicit handling
- Domain-driven design where business errors are distinct from infrastructure errors

## Addressing Common Concerns

Python developers often express skepticism about Result/Option libraries. Here's how unwrappy addresses the most common criticisms:

### "This adds complexity and takes away Python's simplicity"

**unwrappy's approach**: Minimal API surface, no magic.

Unlike some Result libraries that introduce decorators, operators, and functional programming jargon, unwrappy uses familiar Python patterns:

```python
# Feels like isinstance() checks
if result.is_ok():
    value = result.unwrap()

# Native Python 3.10+ pattern matching
match result:
    case Ok(value):
        print(f"Got: {value}")
    case Err(error):
        print(f"Failed: {error}")
```

No special operators, no monadic bind syntax, no type-level magic. Just classes with methods.

### "This doesn't fit Python's try-except flow"

**unwrappy's approach**: Explicit boundaries with `unwrap_or_raise()`.

unwrappy doesn't try to eliminate exceptions—it provides **explicit boundaries** between Result-based code and exception-based code:

```python
# Business logic uses Result
def get_user(user_id: str) -> Result[User, str]:
    ...

# API boundary converts to exceptions
@app.get("/users/{user_id}")
def get_user_endpoint(user_id: str):
    result = get_user(user_id)
    return result.unwrap_or_raise(lambda e: HTTPException(404, e))
```

Use Result in your domain logic where explicit error handling matters. Use exceptions at system boundaries (HTTP handlers, CLI entry points) where frameworks expect them.

### "A mixed codebase is annoying to work with"

**unwrappy's approach**: Designed for mixed codebases.

unwrappy explicitly rejects the "all-or-nothing" philosophy:

- FastAPI routes using `HTTPException` (the framework idiom)
- Service layer returning `Result` (explicit domain errors)
- External library calls wrapped explicitly where needed

### "The @safe decorator gets abused"

**unwrappy's approach**: No `@safe` decorator at all.

Many Result libraries provide decorators like `@safe` or `@as_result` that automatically convert exceptions to `Err`. unwrappy intentionally omits these because:

1. **Decorator stacking problems**: Real code already has `@app.route`, `@login_required`, `@cache`, etc.
2. **Hidden behavior**: A decorator silently catching exceptions makes debugging harder
3. **Overly broad catching**: `@safe` catches all exceptions, including bugs like `NameError`

Instead, unwrappy requires explicit error handling at the point where it matters.

### "This requires all-or-nothing commitment"

**unwrappy's approach**: Adopt incrementally, use at boundaries you control.

You can use unwrappy in:

- A single module for complex parsing logic
- Service layer functions while keeping framework idioms elsewhere
- New code while leaving legacy code unchanged

## Design Philosophy

unwrappy brings Rust's `Result` and `Option` types to Python with these principles:

1. **Errors as values**: Exceptions are implicit control flow; Result makes errors explicit
2. **Type safety**: Full generic support for static analysis
3. **Functional composition**: Rich combinator API for transformation chains
4. **Async ergonomics**: LazyResult solves the "async sandwich" problem

## Type System

```
Ok[T]    - Success variant (single type parameter)
Err[E]   - Error variant (single type parameter)
Result[T, E] = Ok[T] | Err[E]  - Type alias (union)
LazyResult[T, E] - Deferred execution wrapper

Some[T]  - Present variant (single type parameter)
Nothing  - Absent variant (singleton type)
Option[T] = Some[T] | Nothing  - Type alias (union)
LazyOption[T] - Deferred execution wrapper
```

## Design Evolution

### Original Design: ABC Pattern

The first implementation used an Abstract Base Class pattern:

```python
class Result(ABC, Generic[T, E]):
    @abstractmethod
    def is_ok(self) -> bool: ...
    @abstractmethod
    def map(self, fn: Callable[[T], U]) -> Result[U, E]: ...

class Ok(Result[T, E]):
    def is_ok(self) -> bool: return True

class Err(Result[T, E]):
    def is_err(self) -> bool: return True
```

### The Type Inference Problem

Running `pyright` revealed **295 type errors**. The root cause:

```python
ok = Ok(42)
# Inferred type: Ok[int, Unknown]
#                      ^^^^^^^
# The E parameter has no source, so it becomes Unknown
```

With dual type parameters `Ok[T, E]`, creating `Ok(42)` gives the type checker no information about `E`. This cascaded into unusable type inference.

### Solution: Union Type Alias Pattern

Adopting the pattern from [rustedpy/result](https://github.com/rustedpy/result):

```python
class Ok(Generic[T]): ...     # Only T
class Err(Generic[E]): ...    # Only E
Result = Ok[T] | Err[E]       # Type alias, not ABC
```

With single type parameters:

```python
ok = Ok(42)
# Inferred type: Ok[int]  ✓ Precise!

err = Err("failed")
# Inferred type: Err[str]  ✓ Precise!
```

**Trade-off accepted:** Methods are duplicated in Ok and Err classes rather than shared via ABC, but the type safety benefits far outweigh the duplication.

## Key Architectural Decisions

### 1. Type Alias Pattern (Union Types)

Result is a type alias for the union of Ok and Err. This gives precise type inference at the cost of some method duplication.

### 2. LazyResult Deferred Execution

LazyResult builds an operation queue without executing anything:

```python
# This builds a pipeline, executes nothing
lazy = LazyResult.ok(5).map(double).and_then(validate)

# This executes the entire chain
result = await lazy.collect()
```

Operations are stored as frozen dataclasses for immutability and memory efficiency.

### 3. Unified Sync/Async in LazyResult

LazyResult methods accept both sync and async functions via runtime detection:

```python
lazy.map(sync_fn)           # Works
lazy.map(async_fn)          # Also works
```

### 4. Separate Async Methods on Result

Unlike LazyResult, Result has explicit async variants (`map_async`, `and_then_async`) because Result methods execute immediately.

### 5. Nothing as Singleton

Option's `Nothing` is a singleton (like Python's `None`):

```python
NOTHING = _NothingType()  # Single instance
assert opt is NOTHING     # Identity comparison works
```

### 6. No Exception-Catching Decorators

unwrappy intentionally omits `@safe` or `@as_result` decorators. Explicit error handling at each call site is preferred over hidden exception catching.

## Type Checker Limitations

### Known Issues with ty

ty (Astral's type checker) has documented issues with generic TypeVar inference. When using LazyResult factory methods, ty may infer `Unknown` instead of the expected type parameters.

**Workaround**: Use explicit type annotations:

```python
lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
```

## Comparison with Other Libraries

### vs. rustedpy/result

unwrappy adopted rustedpy's type system pattern. Key differences:

- **`unwrap_or_raise`**: unwrappy takes a factory function for full control over exception creation
- **No `@as_result`**: Explicit error handling preferred
- **LazyResult**: Unique feature for async chaining

### vs. dry-python/returns

dry-python/returns is a comprehensive FP library. unwrappy is focused and lightweight:

- Rust naming (`Ok`/`Err` vs `Success`/`Failure`)
- Built-in `tee()`/`inspect()` for side effects
- Simpler async with LazyResult vs separate Future containers
- Zero dependencies

## File Structure

```
src/unwrappy/
├── __init__.py      # Public API exports
├── result.py        # Result, Ok, Err, LazyResult
├── option.py        # Option, Some, Nothing, LazyOption
├── serde.py         # JSON serialization support
└── exceptions.py    # UnwrapError, ChainedError
```

## Performance Considerations

- **Ok/Err**: Minimal overhead, just value wrapping
- **LazyResult**: Builds tuple of operations, executes sequentially
- **Operation dataclasses**: `slots=True` reduces memory footprint
- **Fail-fast**: Err short-circuits remaining operations

## See Also

- [Getting Started](getting-started.md) - Basic usage
- [Result Guide](guide/result.md) - Complete Result documentation
- [Option Guide](guide/option.md) - Complete Option documentation
- [Lazy Evaluation](guide/lazy-evaluation.md) - Async patterns
