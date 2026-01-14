# Architecture

This document explains the design decisions and architectural choices in unwrappy.

## Design Philosophy

unwrappy brings Rust's `Result` and `Option` types to Python with these principles:

1. **Errors as values**: Exceptions are implicit control flow; Result makes errors explicit
2. **Type safety**: Full generic support for static analysis
3. **Functional composition**: Rich combinator API for transformation chains
4. **Async ergonomics**: LazyResult solves the "async sandwich" problem

## Design Evolution

### Original Design: ABC Pattern

The first implementation used an Abstract Base Class pattern:

```python
class Result(ABC, Generic[T, E]):
    @abstractmethod
    def is_ok(self) -> bool: ...
    @abstractmethod
    def map(self, fn: Callable[[T], U]) -> Result[U, E]: ...
    # ... shared interface

class Ok(Result[T, E]):
    def is_ok(self) -> bool: return True

class Err(Result[T, E]):
    def is_err(self) -> bool: return True
```

**Rationale:**
- Clean inheritance - shared methods defined once on ABC
- Familiar OOP pattern
- `isinstance(x, Result)` works naturally

### The Type Inference Problem

Running `pyright` revealed **295 type errors**. The root cause:

```python
ok = Ok(42)
# Inferred type: Ok[int, Unknown]
#                      ^^^^^^^
# The E parameter has no source, so it becomes Unknown
```

With dual type parameters `Ok[T, E]`, creating `Ok(42)` gives the type checker
no information about `E`. This cascaded into:
- Every Ok/Err creation inferred `Unknown` for the unused parameter
- Type narrowing didn't work properly
- Tests required excessive type annotations

We initially tried suppressing these with `# pyright: ignore` comments and
relaxed configuration, but this was "fooling pyright" rather than fixing the
underlying design flaw.

### Discovery: rustedpy's Approach

Researching how [rustedpy/result](https://github.com/rustedpy/result) handles
this revealed a fundamentally different approach:

```python
# rustedpy pattern
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

### Decision: Adopt rustedpy Pattern

The ABC pattern, while elegant from an OOP perspective, fundamentally conflicts
with Python's type system for this use case. The type alias pattern provides:

- **Precise inference**: `Ok(42)` → `Ok[int]`, not `Ok[int, Unknown]`
- **Better narrowing**: Type checkers can narrow union types effectively
- **Zero pyright errors**: The codebase now passes strict type checking
- **Proven approach**: Battle-tested in rustedpy/result

**Trade-off accepted:** Methods are duplicated in Ok and Err classes rather
than shared via ABC, but the type safety benefits far outweigh the duplication.

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

## Key Architectural Decisions

### 1. Type Alias Pattern (Union Types)

Result is a type alias for the union of Ok and Err:

```python
class Ok(Generic[T]): ...
class Err(Generic[E]): ...
Result: TypeAlias = Ok[T] | Err[E]
```

**Why not ABC?**

An earlier version used `class Result(ABC, Generic[T, E])` with Ok and Err as
subclasses. This caused type inference problems—`Ok(42)` inferred as
`Ok[int, Unknown]` because the error type `E` had no source. The type alias
pattern gives precise inference: `Ok(42)` → `Ok[int]`.

See [Design Evolution](#design-evolution) for the full story.

**Why duplicate methods?**

Without an ABC, methods like `map()`, `and_then()`, etc. are implemented in
both Ok and Err. This duplication is the cost of precise type inference—a
worthwhile trade-off for a type-safety focused library.

### 2. LazyResult Deferred Execution

LazyResult doesn't execute operations immediately. It builds an operation queue:

```python
# This builds a pipeline, executes nothing
lazy = LazyResult.ok(5).map(double).and_then(validate)

# This executes the entire chain
result = await lazy.collect()
```

**Why?**
- Avoids nested `await` chains in async code
- Single `.collect()` executes everything
- Inspired by Polars' lazy evaluation

### 3. Operation Dataclasses

Operations are stored as frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class MapOp:
    fn: Callable[[Any], Any]

@dataclass(frozen=True, slots=True)
class AndThenOp:
    fn: Callable[[Any], Any]

Operation = MapOp | MapErrOp | AndThenOp | OrElseOp | TeeOp | InspectErrOp | FlattenOp
```

**Why?**
- Immutable (frozen) for safety
- Memory efficient (slots)
- Union type enables exhaustive pattern matching in `_execute_op`

### 4. Unified Sync/Async in LazyResult

LazyResult methods accept both sync and async functions:

```python
lazy.map(sync_fn)           # Works
lazy.map(async_fn)          # Also works
lazy.and_then(async_fetch)  # Works too
```

This is achieved via `_maybe_await`:

```python
async def _maybe_await(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await value
    return value
```

**Tradeoff**: We sacrifice some type precision (functions typed as `Callable[[Any], Any]`) for runtime flexibility.

### 5. Type System Approach

LazyResult methods accept both sync and async callables via union types:

```python
def map(self, fn: Callable[[T], U | Awaitable[U]]) -> LazyResult[U, E]:
    return LazyResult(self._source, (*self._operations, MapOp(fn)))
```

**Design decisions:**
- Direct `LazyResult` construction preserves type parameters better than `cast()`
- Union types (`U | Awaitable[U]`) express the sync/async flexibility in signatures
- `cast()` is only used for `flatten()` where the type transformation from `Result[Result[U,E],E]` to `Result[U,E]` cannot be expressed otherwise

**Limitation**: Python's type system cannot fully track type transformations through a heterogeneous operation queue. This is a fundamental limitation, not a design flaw.

### 6. Type Checker Limitations

**Known limitations with ty (Astral's type checker):**

ty has documented issues with generic TypeVar inference ([astral-sh/ty#501](https://github.com/astral-sh/ty/issues/501), [#2030](https://github.com/astral-sh/ty/issues/2030)). When using LazyResult factory methods, ty may infer `Unknown` instead of the expected type parameters.

**Example:**
```python
lazy = LazyResult.ok(42)
result = await lazy.collect()
# ty infers: Result[Unknown, Any]
# Expected:  Result[int, Any]
```

**Workarounds:**
- Use explicit type annotations: `lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))`
- The runtime behavior is always correct; only static type inference is affected
- The test suite uses `# ty: ignore[type-assertion-failure]` comments to document expected types while acknowledging ty's inference limitations

**Why this happens:**
- LazyResult handles sync and async functions uniformly via `_maybe_await()` at runtime
- This polymorphism cannot be fully expressed in Python's static type system
- When async functions are passed, the type checker sees `Callable[..., Awaitable[T]]` but the runtime awaits it, producing `T`
- ty's generic inference is stricter than some other type checkers, surfacing these limitations more visibly

### 7. Separate Async Methods on Result

Unlike LazyResult, Result has explicit async variants:

```python
# Sync
result.map(sync_fn)

# Async (explicit)
await result.map_async(async_fn)
```

**Why?**
- Result methods execute immediately
- Async functions must be awaited
- Explicit is better than implicit for immediate execution

### 8. No Exception-Catching Decorators

Unlike other Result libraries, unwrappy intentionally omits decorators like `@as_result` or `@safe` that convert exception-raising functions into Result-returning functions.

**Why?**

1. **Decorator stacking problem**: Real-world code often uses multiple decorators (`@app.route`, `@login_required`, `@cache`, `@retry`, etc.). Adding `@as_result` creates "decorators on decorators" that:
   - Reduce readability
   - Make debugging harder (stack traces become confusing)
   - Create ordering dependencies between decorators

2. **Explicit over implicit**: Exception catching should be a conscious decision at each call site, not hidden in a decorator that silently swallows errors.

3. **Library composability**: unwrappy is designed to work alongside web frameworks, ORMs, and other libraries that already use decorators heavily. Adding more decorators increases cognitive load.

**Instead, be explicit:**

```python
# Don't hide exception handling in decorators
def parse_config(path: str) -> Result[Config, str]:
    try:
        with open(path) as f:
            return Ok(json.load(f))
    except FileNotFoundError:
        return Err(f"Config not found: {path}")
    except json.JSONDecodeError as e:
        return Err(f"Invalid JSON: {e}")
```

This makes error handling visible and intentional at the point where it matters.

### 9. Option Type Design

Option follows the same type alias pattern as Result, with a key distinction: Nothing is a singleton.

#### Nothing as Singleton

```python
class _NothingType:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

NOTHING = _NothingType()
Nothing = _NothingType  # Type alias for annotations
Option: TypeAlias = Some[T] | _NothingType
```

**Why a singleton?**
- **Memory efficiency**: All "absent" values share one instance
- **Identity comparison**: `opt is NOTHING` works reliably
- **Consistency**: Mirrors Python's `None` singleton pattern

#### Option vs typing.Optional

Python's `Optional[T]` is just `T | None`—it doesn't distinguish between "absent" and "null". Option makes this explicit:

```python
# typing.Optional - ambiguous
def get_name() -> str | None:
    return None  # Is this "no name" or "name is explicitly null"?

# unwrappy.Option - clear distinction
def get_name() -> Option[str]:
    return Some("Alice")  # Has a name
    return NOTHING        # No name

# Advanced: Option[T | None] for three-state logic (e.g., PATCH updates)
@dataclass
class UserUpdate:
    # NOTHING = don't update, Some(None) = set to null, Some(value) = set value
    name: Option[str | None] = NOTHING
```

#### Bidirectional Conversion with Result

Option and Result convert cleanly in both directions:

```python
# Option → Result
opt.ok_or("missing value")      # Some(x) → Ok(x), NOTHING → Err("missing value")
opt.ok_or_else(lambda: "err")   # Lazy error creation

# Result → Option
result.ok()   # Ok(x) → Some(x), Err(_) → NOTHING
result.err()  # Err(e) → Some(e), Ok(_) → NOTHING
```

This enables seamless composition between error handling and optional value patterns.

## Serialization Support

unwrappy provides JSON serialization support through the `serde` module, enabling integration with distributed task frameworks like Celery, Temporal, and DBOS.

### JSON Serialization

The `unwrappy.serde` module provides JSON encoder/decoder support:

```python
import json
from unwrappy import Ok, Err, Some, NOTHING
from unwrappy.serde import ResultEncoder, result_decoder, dumps, loads

# Using standard json module
encoded = json.dumps(Ok(42), cls=ResultEncoder)
decoded = json.loads(encoded, object_hook=result_decoder)

# Using convenience functions
encoded = dumps(Ok(42))
decoded = loads(encoded)

# Option types work the same way
encoded = dumps(Some("hello"))
decoded = loads(encoded)
```

**JSON Format**:
```json
{"__unwrappy_type__": "Ok", "value": 42}
{"__unwrappy_type__": "Err", "error": "not found"}
{"__unwrappy_type__": "Some", "value": "hello"}
{"__unwrappy_type__": "Nothing"}
```

### LazyResult/LazyOption Serialization Limitation

**Important**: LazyResult and LazyOption cannot be serialized because operations contain callables (lambdas, functions) which are not JSON-serializable. Always call `.collect()` first:

```python
# This will raise TypeError
lazy = LazyResult.ok(42).map(lambda x: x * 2)
dumps(lazy)  # TypeError!

# Do this instead
result = await lazy.collect()  # Get concrete Result
dumps(result)  # Ok!
```

### Framework Integration

#### Celery

Register a custom serializer for Celery:

```python
from kombu.serialization import register
from unwrappy.serde import dumps, loads

register(
    'unwrappy-json',
    dumps,
    loads,
    content_type='application/x-unwrappy-json',
    content_encoding='utf-8'
)

app.conf.update(
    task_serializer='unwrappy-json',
    result_serializer='unwrappy-json',
    accept_content=['unwrappy-json'],
)
```

#### Temporal

Create a custom data converter:

```python
from temporalio.converter import JSONPlainPayloadConverter
from unwrappy.serde import ResultEncoder, result_decoder
import json

class UnwrappyJSONPayloadConverter(JSONPlainPayloadConverter):
    def encode(self, value):
        return json.dumps(value, cls=ResultEncoder).encode()

    def decode(self, data, type_hint):
        return json.loads(data.decode(), object_hook=result_decoder)
```

#### DBOS

Create a custom serializer:

```python
from dbos.serialization import Serializer
from unwrappy.serde import dumps, loads

class UnwrappySerializer(Serializer):
    def serialize(self, obj) -> str:
        return dumps(obj)

    def deserialize(self, data: str):
        return loads(data)
```

## Performance Considerations

- **Ok/Err**: Minimal overhead, just value wrapping
- **LazyResult**: Builds tuple of operations, executes sequentially
- **Operation dataclasses**: `slots=True` reduces memory footprint
- **Fail-fast**: Err short-circuits remaining operations

## Comparison with Rust

| Feature | Rust | unwrappy |
|---------|------|----------|
| Ok/Err variants | ✓ | ✓ |
| Some/None variants | ✓ | ✓ (Some/Nothing) |
| Pattern matching | ✓ | ✓ (Python 3.10+) |
| ? operator | ✓ | ✗ (use and_then) |
| map/and_then | ✓ | ✓ |
| Option ↔ Result | ✓ | ✓ (ok_or, ok, err) |
| Async support | Via futures | Built-in LazyResult/LazyOption |
| Zero-cost | ✓ | Runtime overhead |

## Comparison with Other Python Libraries

unwrappy draws inspiration from existing Python Result implementations while making distinct design choices.

### vs. rustedpy/result

[rustedpy/result](https://github.com/rustedpy/result) is a direct Rust port with similar goals. **Note: rustedpy/result is now in maintenance mode**, which is the primary reason unwrappy exists—to provide an actively maintained alternative with additional features like LazyResult.

unwrappy adopted rustedpy's type system pattern for precise type inference (see [Design Evolution](#design-evolution)).

| Feature | rustedpy/result | unwrappy |
|---------|-----------------|----------|
| Type definition | `Ok[T] \| Err[E]` type alias | `Ok[T] \| Err[E]` type alias |
| Type parameters | Single (`Ok[T]`, `Err[E]`) | Single (`Ok[T]`, `Err[E]`) |
| Value access | `.ok_value` / `.err_value` properties | `.unwrap()` / `.unwrap_err()` methods |
| Type guards | `is_ok(result)` functions | `.is_ok()` methods |
| Exception conversion | `@as_result` decorator | Not provided (explicit by design) |
| Do notation | `do()` generator syntax | Not provided |
| Async support | `do_async()` | LazyResult with unified sync/async |
| `unwrap_or_raise` | ✓ (takes exception class) | ✓ (takes factory function) |

**Key differences:**
- **`unwrap_or_raise` design**: rustedpy takes an exception class (`result.unwrap_or_raise(ValueError)`), unwrappy takes a factory function (`result.unwrap_or_raise(lambda e: ValueError(f"Invalid: {e}"))`). The factory approach gives full control over exception type and message based on the error value—useful for mapping domain errors to HTTP exceptions.
- **No exception decorator**: unwrappy intentionally omits `@as_result`—decorators stack poorly with frameworks like FastAPI, Flask, or Django that already use decorators heavily. Explicit error handling at call sites is preferred over hidden exception catching.
- **LazyResult**: unwrappy's unique contribution—deferred execution for clean async chaining without nested awaits

### vs. dry-python/returns

[dry-python/returns](https://github.com/dry-python/returns) is a comprehensive functional programming library.

| Feature | dry-python/returns | unwrappy |
|---------|-------------------|----------|
| Scope | Full FP toolkit (Maybe, IO, Future, etc.) | Focused on Result |
| Naming | `Success`/`Failure` | `Ok`/`Err` (Rust-style) |
| Bind operation | `.bind()` | `.and_then()` |
| Error recovery | `.lash()` | `.or_else()` |
| Error transform | `.alt()` | `.map_err()` |
| Side effects | Not built-in | `.tee()` / `.inspect()` |
| Swap values | `.swap()` | Not provided |
| Exception decorator | `@safe` | Not provided |
| Mypy plugin | ✓ | ✗ |
| IO tracking | `IO`, `IOResult` containers | Not provided |
| Async | `Future`, `FutureResult` containers | `LazyResult` |

**Key differences:**
- **Focused scope**: unwrappy provides just Result and LazyResult, avoiding the complexity of a full FP library
- **Rust naming**: Uses Rust's `Ok`/`Err` and `and_then`/`or_else` terminology for familiarity
- **Side effect methods**: Built-in `tee()`/`inspect()` for logging and debugging
- **Simpler async**: LazyResult handles async with a single type rather than separate Future containers
- **No purity tracking**: unwrappy doesn't distinguish pure/impure operations—simpler but less rigorous

### Design Philosophy Comparison

| Aspect | rustedpy/result | dry-python/returns | unwrappy |
|--------|-----------------|-------------------|----------|
| Type pattern | Union alias | ABC-based | Union alias |
| Philosophy | Rust port | Full FP paradigm | Practical Rust-inspired |
| Learning curve | Low | High | Low |
| Type safety | Good | Excellent (mypy plugin) | Good |
| Async approach | Generator-based | Separate containers | Unified LazyResult |
| Exception handling | Decorator-based | Decorator-based | Explicit only |

### Why unwrappy?

Choose unwrappy when you want:
- **Zero dependencies**: Pure Python with no external packages—just stdlib
- **Lightweight**: Minimal footprint, no dependencies
- **Rust-familiar API** without learning new terminology
- **Simple async chaining** via LazyResult without multiple container types
- **Side-effect methods** built into the Result type
- **Explicit error handling** without exception-catching decorators

### Dependency Comparison

| Library | Dependencies |
|---------|--------------|
| unwrappy | 0 |
| rustedpy/result | 0 |
| dry-python/returns | 3+ (typing-extensions, etc.) |

unwrappy prioritizes being a lightweight, dependency-free addition to your project.

## File Structure

```
src/unwrappy/
├── __init__.py      # Public API exports
├── result.py        # Result, Ok, Err, LazyResult, sequence_results, traverse_results
├── option.py        # Option, Some, Nothing, LazyOption, sequence_options, traverse_options
├── serde.py         # JSON serialization support
└── exceptions.py    # UnwrapError, ChainedError
```

## Future Considerations

- **Async iterators**: Stream processing with Result
