from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Coroutine, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Literal, NoReturn, TypeAlias, TypeVar, cast

from unwrappy.exceptions import ChainedError, UnwrapError

if TYPE_CHECKING:
    from unwrappy.option import Some, _NothingType

T = TypeVar("T", covariant=True)  # Success type for Ok
E = TypeVar("E", covariant=True)  # Error type for Err
U = TypeVar("U")  # For transformations
F = TypeVar("F")  # For error transformations


class Ok(Generic[T]):
    """Success variant of Result containing a value.

    Args:
        value: The success value to wrap.

    Example:
        >>> result = Ok(42)
        >>> result.unwrap()
        42
        >>> result.is_ok()
        True
    """

    __slots__ = ("_value",)
    __match_args__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self._value == other._value

    def is_ok(self) -> Literal[True]:
        """Return True (this is Ok)."""
        return True

    def is_err(self) -> Literal[False]:
        """Return False (this is not Err)."""
        return False

    def unwrap(self) -> T:
        """Return the Ok value."""
        return self._value

    def unwrap_err(self) -> NoReturn:
        """Raise UnwrapError (cannot get error from Ok)."""
        raise UnwrapError("Called unwrap_err on Ok", self._value)

    def unwrap_or(self, default: object) -> T:
        """Return the Ok value, ignoring the default."""
        return self._value

    def unwrap_or_else(self, fn: Callable[[Any], U]) -> T:
        """Return the Ok value, ignoring the function."""
        return self._value

    def unwrap_or_raise(self, fn: Callable[[Any], BaseException]) -> T:
        """Return the Ok value, ignoring the exception factory."""
        return self._value

    def expect(self, msg: str) -> T:
        """Return the Ok value."""
        return self._value

    def expect_err(self, msg: str) -> NoReturn:
        """Raise UnwrapError with custom message."""
        raise UnwrapError(f"{msg}: {self._value!r}", self._value)

    def ok(self) -> Some[T]:
        """Return the Ok value wrapped in Some."""
        from unwrappy.option import Some

        return Some(self._value)

    def err(self) -> _NothingType:
        """Return Nothing (no error in Ok)."""
        from unwrappy.option import NOTHING

        return NOTHING

    def map(self, fn: Callable[[T], U]) -> Ok[U]:
        """Transform the Ok value."""
        return Ok(fn(self._value))

    def map_or(self, default: U, fn: Callable[[T], U]) -> U:
        """Apply fn to the Ok value."""
        return fn(self._value)

    def map_or_else(self, default_fn: Callable[[Any], U], fn: Callable[[T], U]) -> U:
        """Apply fn to the Ok value."""
        return fn(self._value)

    def map_err(self, fn: Callable[[Any], F]) -> Ok[T]:
        """Return self unchanged (no error to transform)."""
        return self

    def and_then(self, fn: Callable[[T], Ok[U] | Err[F]]) -> Ok[U] | Err[F]:
        """Chain Result-returning operation."""
        return fn(self._value)

    def or_else(self, fn: Callable[[Any], Ok[U] | Err[F]]) -> Ok[T]:
        """Return self (no error to recover from)."""
        return self

    def tee(self, fn: Callable[[T], Any]) -> Ok[T]:
        """Execute fn for side effects, return self."""
        fn(self._value)
        return self

    inspect = tee

    def inspect_err(self, fn: Callable[[Any], Any]) -> Ok[T]:
        """Return self (no error to inspect)."""
        return self

    def flatten(self: Ok[Ok[U] | Err[F]]) -> Ok[U] | Err[F]:
        """Flatten nested Result."""
        return self._value

    def split(self) -> tuple[T, None]:
        """Split into (value, None) tuple."""
        return (self._value, None)

    def lazy(self) -> LazyResult[T, Any]:
        """Convert to LazyResult for deferred chaining."""
        return LazyResult(self)

    async def map_async(self, fn: Callable[[T], Coroutine[Any, Any, U]]) -> Ok[U]:
        """Transform Ok value with async function."""
        return Ok(await fn(self._value))

    async def map_err_async(self, fn: Callable[[Any], Coroutine[Any, Any, F]]) -> Ok[T]:
        """Return self (no error to transform)."""
        return self

    async def and_then_async(self, fn: Callable[[T], Coroutine[Any, Any, Ok[U] | Err[F]]]) -> Ok[U] | Err[F]:
        """Chain async Result-returning operation."""
        return await fn(self._value)

    async def or_else_async(self, fn: Callable[[Any], Coroutine[Any, Any, Ok[U] | Err[F]]]) -> Ok[T]:
        """Return self (no error to recover from)."""
        return self

    def context(self, msg: str) -> Ok[T]:
        """Return self unchanged (no error to add context to)."""
        return self

    def with_context(self, fn: Callable[[], str]) -> Ok[T]:
        """Return self unchanged (no error to add context to)."""
        return self

    def filter(self, predicate: Callable[[T], bool], error: F) -> Ok[T] | Err[F]:
        """Return self if predicate passes, otherwise Err with given error."""
        if predicate(self._value):
            return self
        return Err(error)

    def zip(self, other: Ok[U] | Err[F]) -> Ok[tuple[T, U]] | Err[F]:
        """Combine with another Result into a tuple."""
        if isinstance(other, Ok):
            return Ok((self._value, other.unwrap()))
        return other

    def zip_with(self, other: Ok[U] | Err[F], fn: Callable[[T, U], Any]) -> Ok[Any] | Err[F]:
        """Combine with another Result using a function."""
        if isinstance(other, Ok):
            return Ok(fn(self._value, other.unwrap()))
        return other


class Err(Generic[E]):
    """Error variant of Result containing an error value.

    Args:
        error: The error value to wrap.

    Example:
        >>> result = Err("something went wrong")
        >>> result.unwrap_err()
        'something went wrong'
        >>> result.is_err()
        True
    """

    __slots__ = ("_error",)
    __match_args__ = ("_error",)

    def __init__(self, error: E) -> None:
        self._error = error

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self._error == other._error

    def is_ok(self) -> Literal[False]:
        """Return False (this is not Ok)."""
        return False

    def is_err(self) -> Literal[True]:
        """Return True (this is Err)."""
        return True

    def unwrap(self) -> NoReturn:
        """Raise UnwrapError (cannot get value from Err)."""
        raise UnwrapError("Called unwrap on Err", self._error)

    def unwrap_err(self) -> E:
        """Return the Err value."""
        return self._error

    def unwrap_or(self, default: U) -> U:
        """Return the default value."""
        return default

    def unwrap_or_else(self, fn: Callable[[E], U]) -> U:
        """Compute and return value from error."""
        return fn(self._error)

    def unwrap_or_raise(self, fn: Callable[[E], BaseException]) -> NoReturn:
        """Raise exception created by fn(error)."""
        raise fn(self._error)

    def expect(self, msg: str) -> NoReturn:
        """Raise UnwrapError with custom message."""
        raise UnwrapError(f"{msg}: {self._error!r}", self._error)

    def expect_err(self, msg: str) -> E:
        """Return the Err value."""
        return self._error

    def ok(self) -> _NothingType:
        """Return Nothing (no value in Err)."""
        from unwrappy.option import NOTHING

        return NOTHING

    def err(self) -> Some[E]:
        """Return the Err value wrapped in Some."""
        from unwrappy.option import Some

        return Some(self._error)

    def map(self, fn: Callable[[Any], U]) -> Err[E]:
        """Return self unchanged (no value to transform)."""
        return self

    def map_or(self, default: U, fn: Callable[[Any], U]) -> U:
        """Return the default value."""
        return default

    def map_or_else(self, default_fn: Callable[[E], U], fn: Callable[[Any], U]) -> U:
        """Apply default_fn to the error."""
        return default_fn(self._error)

    def map_err(self, fn: Callable[[E], F]) -> Err[F]:
        """Transform the Err value."""
        return Err(fn(self._error))

    def and_then(self, fn: Callable[[Any], Ok[U] | Err[F]]) -> Err[E]:
        """Return self (no value to chain)."""
        return self

    def or_else(self, fn: Callable[[E], Ok[U] | Err[F]]) -> Ok[U] | Err[F]:
        """Recover from error by calling fn."""
        return fn(self._error)

    def tee(self, fn: Callable[[Any], Any]) -> Err[E]:
        """Return self (no value to inspect)."""
        return self

    inspect = tee

    def inspect_err(self, fn: Callable[[E], Any]) -> Err[E]:
        """Execute fn for side effects, return self."""
        fn(self._error)
        return self

    def flatten(self) -> Err[E]:
        """Return self (already flat)."""
        return self

    def split(self) -> tuple[None, E]:
        """Split into (None, error) tuple."""
        return (None, self._error)

    def lazy(self) -> LazyResult[Any, E]:
        """Convert to LazyResult for deferred chaining."""
        return LazyResult(self)

    async def map_async(self, fn: Callable[[Any], Coroutine[Any, Any, U]]) -> Err[E]:
        """Return self (no value to transform)."""
        return self

    async def map_err_async(self, fn: Callable[[E], Coroutine[Any, Any, F]]) -> Err[F]:
        """Transform Err value with async function."""
        return Err(await fn(self._error))

    async def and_then_async(self, fn: Callable[[Any], Coroutine[Any, Any, Ok[U] | Err[F]]]) -> Err[E]:
        """Return self (no value to chain)."""
        return self

    async def or_else_async(self, fn: Callable[[E], Coroutine[Any, Any, Ok[U] | Err[F]]]) -> Ok[U] | Err[F]:
        """Recover from error with async function."""
        return await fn(self._error)

    def context(self, msg: str) -> Err[ChainedError]:
        """Wrap the error with additional context."""
        return Err(ChainedError(self._error, msg))

    def with_context(self, fn: Callable[[], str]) -> Err[ChainedError]:
        """Wrap the error with lazily computed context."""
        return Err(ChainedError(self._error, fn()))

    def filter(self, predicate: Callable[[Any], bool], error: Any) -> Err[E]:
        """Return self unchanged (already an error)."""
        return self

    def zip(self, other: Ok[U] | Err[Any]) -> Err[E]:
        """Return self (first error wins)."""
        return self

    def zip_with(self, other: Ok[U] | Err[Any], fn: Callable[[Any, U], Any]) -> Err[E]:
        """Return self (first error wins)."""
        return self


Result: TypeAlias = Ok[T] | Err[E]
"""Type alias for the union of Ok and Err."""


@dataclass(frozen=True, slots=True)
class ResultMapOp:
    """Operation that transforms the Ok value."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ResultMapErrOp:
    """Operation that transforms the Err value."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ResultAndThenOp:
    """Operation that chains a Result-returning function on Ok."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ResultOrElseOp:
    """Operation that chains a Result-returning function on Err."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ResultTeeOp:
    """Operation that executes a side effect on Ok."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ResultInspectErrOp:
    """Operation that executes a side effect on Err."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ResultFlattenOp:
    """Operation that flattens nested Result."""

    pass


ResultOperation = (
    ResultMapOp | ResultMapErrOp | ResultAndThenOp | ResultOrElseOp | ResultTeeOp | ResultInspectErrOp | ResultFlattenOp
)


async def _maybe_await(value: U | Awaitable[U]) -> U:
    """Await if awaitable, otherwise return as-is."""
    if inspect.isawaitable(value):
        return await value
    return cast(U, value)


class LazyResult(Generic[T, E]):
    """Lazy Result with deferred execution for clean async chaining.

    LazyResult builds a pipeline of operations that execute only when
    `.collect()` is called. All methods accept both sync and async
    functions transparently, avoiding nested await chains.

    This pattern is inspired by Polars' lazy evaluation - build the
    computation graph, then execute it all at once.

    Type Parameters:
        T: The success value type.
        E: The error value type.

    Example:
        >>> async def fetch_user(id: int) -> Result[User, str]: ...
        >>> async def fetch_profile(user: User) -> Result[Profile, str]: ...
        >>>
        >>> result = await (
        ...     LazyResult.from_awaitable(fetch_user(42))
        ...     .and_then(fetch_profile)   # Async function
        ...     .map(lambda p: p.name)     # Sync function
        ...     .tee(print)                # Side effect
        ...     .collect()
        ... )

    From an existing Result:
        >>> result = await Ok(5).lazy().map(lambda x: x * 2).collect()
        >>> result
        Ok(10)

    Note:
        Operations are stored as frozen dataclasses and executed
        sequentially. Short-circuiting occurs on Err values.
    """

    __slots__ = ("_source", "_operations")

    def __init__(
        self,
        source: Awaitable[Ok[T] | Err[E]] | Ok[T] | Err[E],
        operations: tuple[ResultOperation, ...] = (),
    ) -> None:
        self._source = source
        self._operations = operations

    @classmethod
    def ok(cls, value: U) -> LazyResult[U, Any]:
        """Create LazyResult from a success value."""
        return LazyResult(Ok(value))

    @classmethod
    def err(cls, error: U) -> LazyResult[Any, U]:
        """Create LazyResult from an error value."""
        return LazyResult(Err(error))

    @classmethod
    def from_result(cls, result: Ok[T] | Err[E]) -> LazyResult[T, E]:
        """Create LazyResult from an existing Result."""
        return cls(result)

    @classmethod
    def from_awaitable(cls, awaitable: Awaitable[Ok[T] | Err[E]]) -> LazyResult[T, E]:
        """Create LazyResult from a coroutine/awaitable that returns Result."""
        return cls(awaitable)

    def _chain(self, op: ResultOperation) -> LazyResult[Any, Any]:
        """Internal: create new LazyResult with operation appended."""
        return LazyResult(self._source, (*self._operations, op))

    def map(self, fn: Callable[[T], U | Awaitable[U]]) -> LazyResult[U, E]:
        """Transform Ok value. fn can be sync or async."""
        return cast(LazyResult[U, E], LazyResult(self._source, (*self._operations, ResultMapOp(fn))))

    def map_err(self, fn: Callable[[E], F | Awaitable[F]]) -> LazyResult[T, F]:
        """Transform Err value. fn can be sync or async."""
        return cast(LazyResult[T, F], LazyResult(self._source, (*self._operations, ResultMapErrOp(fn))))

    def and_then(self, fn: Callable[[T], Ok[U] | Err[E] | Awaitable[Ok[U] | Err[E]]]) -> LazyResult[U, E]:
        """Chain Result-returning function. fn can be sync or async."""
        return cast(LazyResult[U, E], LazyResult(self._source, (*self._operations, ResultAndThenOp(fn))))

    def or_else(self, fn: Callable[[E], Ok[T] | Err[F] | Awaitable[Ok[T] | Err[F]]]) -> LazyResult[T, F]:
        """Recover from Err. fn can be sync or async."""
        return cast(LazyResult[T, F], LazyResult(self._source, (*self._operations, ResultOrElseOp(fn))))

    def tee(self, fn: Callable[[T], Any]) -> LazyResult[T, E]:
        """Side effect on Ok value. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, ResultTeeOp(fn)))

    inspect = tee

    def inspect_err(self, fn: Callable[[E], Any]) -> LazyResult[T, E]:
        """Side effect on Err value. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, ResultInspectErrOp(fn)))

    def flatten(self: LazyResult[Ok[U] | Err[E], E]) -> LazyResult[U, E]:
        """Flatten nested LazyResult[Result[U, E], E] to LazyResult[U, E]."""
        return cast(LazyResult[U, E], LazyResult(self._source, (*self._operations, ResultFlattenOp())))

    async def collect(self) -> Ok[T] | Err[E]:
        """Execute the lazy chain and return the final Result."""
        result: Ok[Any] | Err[Any] = await _maybe_await(self._source)

        for op in self._operations:
            result = await self._execute_op(result, op)

        return result

    async def _execute_op(self, result: Ok[Any] | Err[Any], op: ResultOperation) -> Ok[Any] | Err[Any]:
        """Execute a single operation on a Result."""
        match op:
            case ResultMapOp(fn):
                if result.is_ok():
                    value = await _maybe_await(fn(result.unwrap()))
                    return Ok(value)
                return result

            case ResultMapErrOp(fn):
                if result.is_err():
                    error = await _maybe_await(fn(result.unwrap_err()))
                    return Err(error)
                return result

            case ResultAndThenOp(fn):
                if result.is_ok():
                    return await _maybe_await(fn(result.unwrap()))
                return result

            case ResultOrElseOp(fn):
                if result.is_err():
                    return await _maybe_await(fn(result.unwrap_err()))
                return result

            case ResultTeeOp(fn):
                if result.is_ok():
                    await _maybe_await(fn(result.unwrap()))
                return result

            case ResultInspectErrOp(fn):
                if result.is_err():
                    await _maybe_await(fn(result.unwrap_err()))
                return result

            case ResultFlattenOp():
                if result.is_ok():
                    return result.unwrap()
                return result

        return result


def sequence_results(results: Iterable[Ok[T] | Err[E]]) -> Ok[list[T]] | Err[E]:
    """Collect an iterable of Results into a Result of list.

    Fails fast on the first Err encountered, returning that error.
    If all Results are Ok, returns Ok containing a list of all values.

    Args:
        results: Iterable of Result values to collect.

    Returns:
        Ok(list) if all are Ok, otherwise the first Err.

    Example:
        >>> sequence([Ok(1), Ok(2), Ok(3)])
        Ok([1, 2, 3])
        >>> sequence([Ok(1), Err("fail"), Ok(3)])
        Err('fail')
        >>> sequence([])
        Ok([])
    """
    values: list[T] = []
    for r in results:
        if r.is_err():
            return Err(r.unwrap_err())
        values.append(r.unwrap())
    return Ok(values)


def traverse_results(items: Iterable[U], fn: Callable[[U], Ok[T] | Err[E]]) -> Ok[list[T]] | Err[E]:
    """Map a function over items and collect Results.

    Equivalent to `sequence_results(map(fn, items))` but more efficient.
    Fails fast on the first Err encountered.

    Args:
        items: Iterable of items to process.
        fn: Function returning Result for each item.

    Returns:
        Ok(list) if all succeed, otherwise the first Err.

    Example:
        >>> def parse_int(s: str) -> Result[int, str]:
        ...     try:
        ...         return Ok(int(s))
        ...     except ValueError:
        ...         return Err(f"invalid: {s}")
        >>> traverse_results(["1", "2", "3"], parse_int)
        Ok([1, 2, 3])
        >>> traverse_results(["1", "x", "3"], parse_int)
        Err('invalid: x')
    """
    return sequence_results(fn(item) for item in items)
