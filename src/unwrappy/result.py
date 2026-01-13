from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Coroutine, Generic, Iterable, TypeVar, cast

from unwrappy.exceptions import UnwrapError

T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped success
F = TypeVar("F")  # Mapped error


class Result(ABC, Generic[T, E]):
    """A Rust-like Result type for safe error handling without exceptions.

    Result represents the outcome of an operation that can either succeed
    with a value (Ok) or fail with an error (Err). This enables explicit
    error handling through pattern matching and combinators.

    Type Parameters:
        T: The success value type.
        E: The error value type.

    Example:
        >>> def divide(a: int, b: int) -> Result[float, str]:
        ...     if b == 0:
        ...         return Err("division by zero")
        ...     return Ok(a / b)
        ...
        >>> match divide(10, 2):
        ...     case Ok(value):
        ...         print(f"Result: {value}")
        ...     case Err(error):
        ...         print(f"Error: {error}")
    """

    @abstractmethod
    def is_ok(self) -> bool:
        """Return True if the result is Ok.

        Example:
            >>> Ok(5).is_ok()
            True
            >>> Err("fail").is_ok()
            False
        """
        ...

    @abstractmethod
    def unwrap(self) -> T:
        """Return the Ok value, or raise UnwrapError if Err.

        Raises:
            UnwrapError: If the result is Err.

        Example:
            >>> Ok(5).unwrap()
            5
            >>> Err("fail").unwrap()  # Raises UnwrapError
        """
        ...

    @abstractmethod
    def unwrap_err(self) -> E:
        """Return the Err value, or raise UnwrapError if Ok.

        Raises:
            UnwrapError: If the result is Ok.

        Example:
            >>> Err("fail").unwrap_err()
            'fail'
            >>> Ok(5).unwrap_err()  # Raises UnwrapError
        """
        ...

    def is_err(self) -> bool:
        """Return True if the result is Err.

        Example:
            >>> Err("fail").is_err()
            True
            >>> Ok(5).is_err()
            False
        """
        return not self.is_ok()

    def expect(self, msg: str) -> T:
        """Return Ok value or raise UnwrapError with custom message.

        Args:
            msg: Error message prefix if Err.

        Raises:
            UnwrapError: If the result is Err, with msg and error value.

        Example:
            >>> Ok(5).expect("should have value")
            5
            >>> Err("fail").expect("should have value")  # Raises: "should have value: 'fail'"
        """
        if self.is_ok():
            return self.unwrap()
        raise UnwrapError(f"{msg}: {self.unwrap_err()!r}", self.unwrap_err())

    def expect_err(self, msg: str) -> E:
        """Return Err value or raise UnwrapError with custom message.

        Args:
            msg: Error message prefix if Ok.

        Raises:
            UnwrapError: If the result is Ok, with msg and ok value.

        Example:
            >>> Err("fail").expect_err("should have error")
            'fail'
        """
        if self.is_err():
            return self.unwrap_err()
        raise UnwrapError(f"{msg}: {self.unwrap()!r}", self.unwrap())

    def unwrap_or(self, default: T) -> T:
        """Return Ok value or the provided default.

        Args:
            default: Value to return if Err.

        Example:
            >>> Ok(5).unwrap_or(0)
            5
            >>> Err("fail").unwrap_or(0)
            0
        """
        return self.unwrap() if self.is_ok() else default

    def unwrap_or_else(self, fn: Callable[[E], T]) -> T:
        """Return Ok value or compute default from error.

        Args:
            fn: Function to compute default from error value.

        Example:
            >>> Ok(5).unwrap_or_else(lambda e: len(e))
            5
            >>> Err("fail").unwrap_or_else(lambda e: len(e))
            4
        """
        return self.unwrap() if self.is_ok() else fn(self.unwrap_err())

    def unwrap_or_raise(self, fn: Callable[[E], BaseException]) -> T:
        """Return Ok value or raise exception created by fn(error).

        Useful at API boundaries where domain errors map to HTTP exceptions.

        Args:
            fn: Function that takes error value and returns an exception to raise.

        Returns:
            The Ok value if Ok.

        Raises:
            BaseException: The exception returned by fn(error) if Err.

        Example:
            >>> Ok(5).unwrap_or_raise(lambda e: ValueError(str(e)))
            5
            >>> Err("bad").unwrap_or_raise(lambda e: ValueError(f"Invalid: {e}"))
            # Raises ValueError("Invalid: bad")
        """
        if self.is_ok():
            return self.unwrap()
        raise fn(self.unwrap_err())

    def ok(self) -> T | None:
        """Return Ok value or None.

        Example:
            >>> Ok(5).ok()
            5
            >>> Err("fail").ok()
            None
        """
        return self.unwrap() if self.is_ok() else None

    def err(self) -> E | None:
        """Return Err value or None.

        Example:
            >>> Err("fail").err()
            'fail'
            >>> Ok(5).err()
            None
        """
        return self.unwrap_err() if self.is_err() else None

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform the Ok value, leaving Err unchanged.

        Args:
            fn: Function to apply to the Ok value.

        Returns:
            Ok(fn(value)) if Ok, otherwise the original Err.

        Example:
            >>> Ok(5).map(lambda x: x * 2)
            Ok(10)
            >>> Err("fail").map(lambda x: x * 2)
            Err('fail')
        """
        if self.is_ok():
            return Ok(fn(self.unwrap()))
        return Err(self.unwrap_err())

    def map_or(self, default: U, fn: Callable[[T], U]) -> U:
        """Apply fn to Ok value, or return default for Err.

        Args:
            default: Value to return if Err.
            fn: Function to apply if Ok.

        Example:
            >>> Ok(5).map_or(0, lambda x: x * 2)
            10
            >>> Err("fail").map_or(0, lambda x: x * 2)
            0
        """
        return fn(self.unwrap()) if self.is_ok() else default

    def map_or_else(self, default_fn: Callable[[E], U], fn: Callable[[T], U]) -> U:
        """Apply fn to Ok value, or default_fn to Err value.

        Args:
            default_fn: Function to apply to error if Err.
            fn: Function to apply to value if Ok.

        Example:
            >>> Ok(5).map_or_else(len, lambda x: x * 2)
            10
            >>> Err("fail").map_or_else(len, lambda x: x * 2)
            4
        """
        return fn(self.unwrap()) if self.is_ok() else default_fn(self.unwrap_err())

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        """Transform the Err value, leaving Ok unchanged.

        Args:
            fn: Function to apply to the Err value.

        Returns:
            Err(fn(error)) if Err, otherwise the original Ok.

        Example:
            >>> Err("fail").map_err(str.upper)
            Err('FAIL')
            >>> Ok(5).map_err(str.upper)
            Ok(5)
        """
        if self.is_err():
            return Err(fn(self.unwrap_err()))
        return Ok(self.unwrap())

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain Result-returning operations (flatMap/bind).

        Args:
            fn: Function returning a Result to chain on success.

        Returns:
            fn(value) if Ok, otherwise the original Err.

        Example:
            >>> def validate(x: int) -> Result[int, str]:
            ...     return Ok(x) if x > 0 else Err("must be positive")
            >>> Ok(5).and_then(validate)
            Ok(5)
            >>> Ok(-1).and_then(validate)
            Err('must be positive')
        """
        return fn(self.unwrap()) if self.is_ok() else Err(self.unwrap_err())

    def or_else(self, fn: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Handle Err by calling fn, passing through Ok unchanged.

        Args:
            fn: Function returning a Result to recover from error.

        Returns:
            The original Ok, or fn(error) if Err.

        Example:
            >>> def fallback(e: str) -> Result[int, str]:
            ...     return Ok(0)
            >>> Err("fail").or_else(fallback)
            Ok(0)
            >>> Ok(5).or_else(fallback)
            Ok(5)
        """
        return Ok(self.unwrap()) if self.is_ok() else fn(self.unwrap_err())

    def tee(self, fn: Callable[[T], Any]) -> Result[T, E]:
        """Execute fn on Ok value for side effects, return self unchanged.

        Also aliased as `inspect()`.

        Args:
            fn: Side-effect function to call with Ok value.

        Returns:
            The original Result unchanged.

        Example:
            >>> Ok(5).tee(print).map(lambda x: x * 2)
            5
            Ok(10)
        """
        if self.is_ok():
            fn(self.unwrap())
        return self

    inspect = tee

    def inspect_err(self, fn: Callable[[E], Any]) -> Result[T, E]:
        """Execute fn on Err value for side effects, return self unchanged.

        Args:
            fn: Side-effect function to call with Err value.

        Returns:
            The original Result unchanged.

        Example:
            >>> Err("fail").inspect_err(print).map_err(str.upper)
            fail
            Err('FAIL')
        """
        if self.is_err():
            fn(self.unwrap_err())
        return self

    def flatten(self: Result[Result[U, E], E]) -> Result[U, E]:
        """Flatten nested Result[Result[U, E], E] to Result[U, E].

        Removes one level of nesting from a nested Result.

        Example:
            >>> Ok(Ok(5)).flatten()
            Ok(5)
            >>> Ok(Err("inner")).flatten()
            Err('inner')
            >>> Err("outer").flatten()
            Err('outer')
        """
        if self.is_ok():
            return self.unwrap()
        return Err(self.unwrap_err())

    def split(self) -> tuple[T | None, E | None]:
        """Split Result into (value, error) tuple for Go-style handling.

        Returns:
            (value, None) if Ok, (None, error) if Err.

        Example:
            >>> value, err = Ok(5).split()
            >>> value
            5
            >>> value, err = Err("fail").split()
            >>> err
            'fail'
        """
        if self.is_ok():
            return (self.unwrap(), None)
        return (None, self.unwrap_err())

    def lazy(self) -> LazyResult[T, E]:
        """Convert to LazyResult for deferred async chaining.

        Returns:
            LazyResult wrapping this Result for deferred operations.

        Example:
            >>> result = await Ok(5).lazy().map(lambda x: x * 2).collect()
            >>> result
            Ok(10)
        """
        return LazyResult.from_result(self)

    async def map_async(
        self, fn: Callable[[T], Coroutine[Any, Any, U]]
    ) -> Result[U, E]:
        """Transform Ok value with an async function.

        Args:
            fn: Async function to apply to the Ok value.

        Returns:
            Ok(await fn(value)) if Ok, otherwise the original Err.

        Example:
            >>> async def fetch_name(id: int) -> str:
            ...     return f"User-{id}"
            >>> await Ok(42).map_async(fetch_name)
            Ok('User-42')
        """
        if self.is_ok():
            return Ok(await fn(self.unwrap()))
        return Err(self.unwrap_err())

    async def map_err_async(
        self, fn: Callable[[E], Coroutine[Any, Any, F]]
    ) -> Result[T, F]:
        """Transform Err value with an async function.

        Args:
            fn: Async function to apply to the Err value.

        Returns:
            Err(await fn(error)) if Err, otherwise the original Ok.
        """
        if self.is_err():
            return Err(await fn(self.unwrap_err()))
        return Ok(self.unwrap())

    async def and_then_async(
        self, fn: Callable[[T], Coroutine[Any, Any, Result[U, E]]]
    ) -> Result[U, E]:
        """Chain async Result-returning operations.

        Args:
            fn: Async function returning a Result to chain on success.

        Returns:
            await fn(value) if Ok, otherwise the original Err.

        Example:
            >>> async def fetch_profile(user_id: int) -> Result[dict, str]:
            ...     return Ok({"id": user_id, "name": "Alice"})
            >>> await Ok(42).and_then_async(fetch_profile)
            Ok({'id': 42, 'name': 'Alice'})
        """
        return await fn(self.unwrap()) if self.is_ok() else Err(self.unwrap_err())

    async def or_else_async(
        self, fn: Callable[[E], Coroutine[Any, Any, Result[T, F]]]
    ) -> Result[T, F]:
        """Handle Err with async recovery function.

        Args:
            fn: Async function returning a Result to recover from error.

        Returns:
            The original Ok, or await fn(error) if Err.
        """
        return Ok(self.unwrap()) if self.is_ok() else await fn(self.unwrap_err())


class Ok(Result[T, E]):
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

    __match_args__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self._value == other._value

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> T:
        return self._value

    def unwrap_err(self) -> E:
        raise UnwrapError("Called unwrap_err on Ok", self._value)


class Err(Result[T, E]):
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

    __match_args__ = ("_error",)

    def __init__(self, error: E) -> None:
        self._error = error

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self._error == other._error

    def is_ok(self) -> bool:
        return False

    def unwrap(self) -> T:
        raise UnwrapError("Called unwrap on Err", self._error)

    def unwrap_err(self) -> E:
        return self._error


@dataclass(frozen=True, slots=True)
class MapOp:
    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class MapErrOp:
    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class AndThenOp:
    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class OrElseOp:
    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class TeeOp:
    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class InspectErrOp:
    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class FlattenOp:
    pass


Operation = MapOp | MapErrOp | AndThenOp | OrElseOp | TeeOp | InspectErrOp | FlattenOp


async def _maybe_await(value: T | Awaitable[T]) -> T:
    """Await if awaitable, otherwise return as-is."""
    if inspect.isawaitable(value):
        return await value
    return value


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
        source: Awaitable[Result[T, E]] | Result[T, E],
        operations: tuple[Operation, ...] = (),
    ) -> None:
        self._source = source
        self._operations = operations

    @classmethod
    def ok(cls, value: T) -> LazyResult[T, Any]:
        """Create LazyResult from a success value."""
        return cls(Ok(value))

    @classmethod
    def err(cls, error: E) -> LazyResult[Any, E]:
        """Create LazyResult from an error value."""
        return cls(Err(error))

    @classmethod
    def from_result(cls, result: Result[T, E]) -> LazyResult[T, E]:
        """Create LazyResult from an existing Result."""
        return cls(result)

    @classmethod
    def from_awaitable(cls, awaitable: Awaitable[Result[T, E]]) -> LazyResult[T, E]:
        """Create LazyResult from a coroutine/awaitable that returns Result."""
        return cls(awaitable)

    def _chain(self, op: Operation) -> LazyResult[Any, Any]:
        """Internal: create new LazyResult with operation appended."""
        return LazyResult(self._source, (*self._operations, op))

    def map(self, fn: Callable[[T], U | Awaitable[U]]) -> LazyResult[U, E]:
        """Transform Ok value. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, MapOp(fn)))

    def map_err(self, fn: Callable[[E], F | Awaitable[F]]) -> LazyResult[T, F]:
        """Transform Err value. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, MapErrOp(fn)))

    def and_then(
        self, fn: Callable[[T], Result[U, E] | Awaitable[Result[U, E]]]
    ) -> LazyResult[U, E]:
        """Chain Result-returning function. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, AndThenOp(fn)))

    def or_else(
        self, fn: Callable[[E], Result[T, F] | Awaitable[Result[T, F]]]
    ) -> LazyResult[T, F]:
        """Recover from Err. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, OrElseOp(fn)))

    def tee(self, fn: Callable[[T], Any]) -> LazyResult[T, E]:
        """Side effect on Ok value. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, TeeOp(fn)))

    inspect = tee

    def inspect_err(self, fn: Callable[[E], Any]) -> LazyResult[T, E]:
        """Side effect on Err value. fn can be sync or async."""
        return LazyResult(self._source, (*self._operations, InspectErrOp(fn)))

    def flatten(self: LazyResult[Result[U, E], E]) -> LazyResult[U, E]:
        """Flatten nested LazyResult[Result[U, E], E] to LazyResult[U, E]."""
        # cast needed: type transformation from Result[Result[U,E],E] -> Result[U,E]
        return cast(LazyResult[U, E], LazyResult(self._source, (*self._operations, FlattenOp())))

    async def collect(self) -> Result[T, E]:
        """Execute the lazy chain and return the final Result."""
        result: Result[Any, Any] = await _maybe_await(self._source)

        for op in self._operations:
            result = await self._execute_op(result, op)

        return result

    async def _execute_op(
        self, result: Result[Any, Any], op: Operation
    ) -> Result[Any, Any]:
        """Execute a single operation on a Result."""
        match op:
            case MapOp(fn):
                if result.is_ok():
                    value = await _maybe_await(fn(result.unwrap()))
                    return Ok(value)
                return result

            case MapErrOp(fn):
                if result.is_err():
                    error = await _maybe_await(fn(result.unwrap_err()))
                    return Err(error)
                return result

            case AndThenOp(fn):
                if result.is_ok():
                    return await _maybe_await(fn(result.unwrap()))
                return result

            case OrElseOp(fn):
                if result.is_err():
                    return await _maybe_await(fn(result.unwrap_err()))
                return result

            case TeeOp(fn):
                if result.is_ok():
                    await _maybe_await(fn(result.unwrap()))
                return result

            case InspectErrOp(fn):
                if result.is_err():
                    await _maybe_await(fn(result.unwrap_err()))
                return result

            case FlattenOp():
                if result.is_ok():
                    return result.unwrap()
                return result

        return result  # Unreachable, but satisfies type checker


def sequence(results: Iterable[Result[T, E]]) -> Result[list[T], E]:
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


def traverse(items: Iterable[U], fn: Callable[[U], Result[T, E]]) -> Result[list[T], E]:
    """Map a function over items and collect Results.

    Equivalent to `sequence(map(fn, items))` but more efficient.
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
        >>> traverse(["1", "2", "3"], parse_int)
        Ok([1, 2, 3])
        >>> traverse(["1", "x", "3"], parse_int)
        Err('invalid: x')
    """
    return sequence(fn(item) for item in items)
