# Lazy Evaluation

`LazyResult` and `LazyOption` provide deferred execution for building async operation pipelines without nested awaits.

## The Problem with Async Chains

Traditional async code requires nested awaits:

```python
async def fetch_user(id: int) -> Result[User, str]: ...
async def fetch_posts(user: User) -> Result[list[Post], str]: ...
async def fetch_comments(post: Post) -> Result[list[Comment], str]: ...

# Without LazyResult - nested awaits everywhere
user_result = await fetch_user(42)
if user_result.is_err():
    return user_result

posts_result = await fetch_posts(user_result.unwrap())
if posts_result.is_err():
    return posts_result

# ... and so on
```

Or with `and_then_async`, you still need multiple awaits:

```python
result = await (await fetch_user(42)).and_then_async(fetch_posts)
```

## LazyResult Solution

LazyResult builds an operation queue without executing anything, then runs the entire chain with a single `await`:

```python
from unwrappy import LazyResult

result = await (
    LazyResult.from_awaitable(fetch_user(42))
    .and_then(fetch_posts)
    .map(lambda posts: len(posts))
    .tee(lambda n: print(f"Found {n} posts"))
    .collect()
)
```

The key insight: **build the pipeline, execute once**.

## Creating LazyResults

### From an Awaitable

```python
async def fetch_data() -> Result[Data, str]: ...

lazy = LazyResult.from_awaitable(fetch_data())
```

### From an Existing Result

```python
lazy = LazyResult.from_result(Ok(42))
lazy = LazyResult.from_result(Err("oops"))
```

### Factory Methods

```python
lazy = LazyResult.ok(42)       # Wraps Ok(42)
lazy = LazyResult.err("oops")  # Wraps Err("oops")
```

## Transformation Methods

LazyResult supports all the same methods as Result, but deferred:

### Transform Ok Value

```python
lazy = (
    LazyResult.ok(5)
    .map(lambda x: x * 2)      # Sync function
    .map(async_transform)      # Async function - also works!
)
```

### Transform Err Value

```python
lazy = (
    LazyResult.err("error")
    .map_err(lambda e: f"wrapped: {e}")
)
```

### Chain Result-Returning Functions

```python
async def validate(data: Data) -> Result[ValidData, str]: ...
async def process(data: ValidData) -> Result[Output, str]: ...

lazy = (
    LazyResult.from_awaitable(fetch_data())
    .and_then(validate)   # Async function
    .and_then(process)    # Async function
)
```

### Recover from Errors

```python
async def try_backup(e: str) -> Result[Data, str]: ...

lazy = (
    LazyResult.from_awaitable(primary_fetch())
    .or_else(try_backup)  # Called only if primary fails
)
```

### Side Effects

```python
lazy = (
    LazyResult.ok(42)
    .tee(lambda x: print(f"Value: {x}"))          # Sync
    .tee(async_log)                                # Async
    .inspect_err(lambda e: logger.error(e))
)
```

### Unwrap Nested Results

```python
# If your function returns Result[Result[T, E], E]
lazy = LazyResult.ok(Ok(42)).flatten()  # Produces Ok(42)
```

## Executing the Pipeline

### Execute and Get Result

```python
result = await lazy.collect()  # Returns Result[T, E]

match result:
    case Ok(value):
        print(f"Success: {value}")
    case Err(error):
        print(f"Error: {error}")
```

!!! important
    `collect()` is the only way to execute a LazyResult pipeline. All operations before `collect()` are deferred.

## Mixing Sync and Async

LazyResult transparently handles both sync and async functions:

```python
def double(x: int) -> int:
    return x * 2

async def fetch_multiplier() -> int:
    return await some_async_call()

async def multiply(x: int) -> Result[int, str]:
    m = await fetch_multiplier()
    return Ok(x * m)

result = await (
    LazyResult.ok(5)
    .map(double)           # Sync - no await needed
    .and_then(multiply)    # Async - handled automatically
    .map(double)           # Sync again
    .collect()
)
```

## LazyOption

`LazyOption` works the same way for Option types:

```python
from unwrappy import LazyOption, Some, NOTHING

async def fetch_config(key: str) -> Option[str]: ...
async def parse_value(s: str) -> Option[int]: ...

result = await (
    LazyOption.from_awaitable(fetch_config("timeout"))
    .and_then(parse_value)
    .map(lambda x: x * 1000)  # Convert to milliseconds
    .collect()
)
```

### Creating LazyOptions

```python
lazy = LazyOption.from_awaitable(async_option_func())
lazy = LazyOption.from_option(Some(42))
lazy = LazyOption.some(42)
lazy = LazyOption.nothing()
```

### LazyOption Methods

All Option methods are available:

- `map(fn)` - Transform Some value
- `and_then(fn)` - Chain Option-returning function
- `or_else(fn)` - Provide alternative
- `filter(predicate)` - Keep if predicate passes
- `tee(fn)` / `inspect(fn)` - Side effect on Some
- `inspect_nothing(fn)` - Side effect on Nothing
- `flatten()` - Unwrap nested Options
- `collect()` - Execute and get Option

## Real-World Example

A complete async service composition:

```python
from unwrappy import LazyResult, Ok, Err, Result
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str

@dataclass
class Profile:
    user: User
    posts_count: int
    followers_count: int

async def fetch_user(user_id: int) -> Result[User, str]:
    # Simulate DB call
    if user_id <= 0:
        return Err("invalid user id")
    return Ok(User(user_id, "Alice"))

async def fetch_posts_count(user: User) -> Result[int, str]:
    # Simulate API call
    return Ok(42)

async def fetch_followers_count(user: User) -> Result[int, str]:
    # Simulate API call
    return Ok(100)

async def build_profile(user_id: int) -> Result[Profile, str]:
    # First, get the user
    user_result = await LazyResult.from_awaitable(
        fetch_user(user_id)
    ).collect()

    if user_result.is_err():
        return user_result  # type: ignore

    user = user_result.unwrap()

    # Then fetch counts in parallel (using regular async)
    import asyncio
    posts_result, followers_result = await asyncio.gather(
        LazyResult.from_awaitable(fetch_posts_count(user)).collect(),
        LazyResult.from_awaitable(fetch_followers_count(user)).collect(),
    )

    # Combine results
    return (
        posts_result
        .and_then(lambda posts:
            followers_result.map(lambda followers:
                Profile(user, posts, followers)
            )
        )
    )

# Usage
profile = await build_profile(42)
match profile:
    case Ok(p):
        print(f"{p.user.name}: {p.posts_count} posts, {p.followers_count} followers")
    case Err(e):
        print(f"Error: {e}")
```

## Serialization Limitation

!!! warning "LazyResult cannot be serialized"
    `LazyResult` and `LazyOption` contain function references (lambdas, async functions) which cannot be serialized to JSON.

    Always call `.collect()` before serializing:

    ```python
    from unwrappy import dumps

    # This will raise TypeError
    lazy = LazyResult.ok(42).map(lambda x: x * 2)
    dumps(lazy)  # TypeError!

    # Do this instead
    result = await lazy.collect()
    dumps(result)  # Ok!
    ```

## Performance Considerations

- **Operation queue**: LazyResult builds a tuple of operations, then executes them sequentially
- **Short-circuiting**: Err values skip remaining operations
- **Memory**: Operation dataclasses use `slots=True` for minimal footprint
- **No caching**: Each `collect()` re-executes the pipeline

## Type Inference Notes

Due to Python's type system limitations, some type checkers may have trouble inferring types through long LazyResult chains. If needed, add explicit type annotations:

```python
lazy: LazyResult[int, str] = LazyResult.ok(42)
```

See the [Architecture docs](../architecture.md#type-checker-limitations) for more details.
