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
    """A Rust-like Result type: either Ok(value) or Err(error)."""

    @abstractmethod
    def is_ok(self) -> bool: ...

    @abstractmethod
    def unwrap(self) -> T: ...

    @abstractmethod
    def unwrap_err(self) -> E: ...

    def is_err(self) -> bool:
        return not self.is_ok()

    def expect(self, msg: str) -> T:
        if self.is_ok():
            return self.unwrap()
        raise UnwrapError(f"{msg}: {self.unwrap_err()!r}", self.unwrap_err())

    def expect_err(self, msg: str) -> E:
        if self.is_err():
            return self.unwrap_err()
        raise UnwrapError(f"{msg}: {self.unwrap()!r}", self.unwrap())

    def unwrap_or(self, default: T) -> T:
        return self.unwrap() if self.is_ok() else default

    def unwrap_or_else(self, fn: Callable[[E], T]) -> T:
        return self.unwrap() if self.is_ok() else fn(self.unwrap_err())

    def ok(self) -> T | None:
        return self.unwrap() if self.is_ok() else None

    def err(self) -> E | None:
        return self.unwrap_err() if self.is_err() else None

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        if self.is_ok():
            return Ok(fn(self.unwrap()))
        return Err(self.unwrap_err())

    def map_or(self, default: U, fn: Callable[[T], U]) -> U:
        return fn(self.unwrap()) if self.is_ok() else default

    def map_or_else(self, default_fn: Callable[[E], U], fn: Callable[[T], U]) -> U:
        return fn(self.unwrap()) if self.is_ok() else default_fn(self.unwrap_err())

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        if self.is_err():
            return Err(fn(self.unwrap_err()))
        return Ok(self.unwrap())

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return fn(self.unwrap()) if self.is_ok() else Err(self.unwrap_err())

    def or_else(self, fn: Callable[[E], Result[T, F]]) -> Result[T, F]:
        return Ok(self.unwrap()) if self.is_ok() else fn(self.unwrap_err())

    def tee(self, fn: Callable[[T], Any]) -> Result[T, E]:
        """Run fn on Ok value for side effects, return self unchanged."""
        if self.is_ok():
            fn(self.unwrap())
        return self

    inspect = tee

    def inspect_err(self, fn: Callable[[E], Any]) -> Result[T, E]:
        """Run fn on Err value for side effects, return self unchanged."""
        if self.is_err():
            fn(self.unwrap_err())
        return self

    def flatten(self: Result[Result[U, E], E]) -> Result[U, E]:
        """Flatten nested Result[Result[U, E], E] to Result[U, E]."""
        if self.is_ok():
            return self.unwrap()
        return Err(self.unwrap_err())

    def split(self) -> tuple[T | None, E | None]:
        """Split Result into (value, error) tuple for Go-style handling.

        Ok(5).split()    → (5, None)
        Err("x").split() → (None, "x")
        """
        if self.is_ok():
            return (self.unwrap(), None)
        return (None, self.unwrap_err())

    def lazy(self) -> LazyResult[T, E]:
        """Convert to LazyResult for deferred async chaining.

        Ok(5).lazy().map(f).and_then(g).collect()
        """
        return LazyResult.from_result(self)

    async def map_async(
        self, fn: Callable[[T], Coroutine[Any, Any, U]]
    ) -> Result[U, E]:
        if self.is_ok():
            return Ok(await fn(self.unwrap()))
        return Err(self.unwrap_err())

    async def map_err_async(
        self, fn: Callable[[E], Coroutine[Any, Any, F]]
    ) -> Result[T, F]:
        if self.is_err():
            return Err(await fn(self.unwrap_err()))
        return Ok(self.unwrap())

    async def and_then_async(
        self, fn: Callable[[T], Coroutine[Any, Any, Result[U, E]]]
    ) -> Result[U, E]:
        return await fn(self.unwrap()) if self.is_ok() else Err(self.unwrap_err())

    async def or_else_async(
        self, fn: Callable[[E], Coroutine[Any, Any, Result[T, F]]]
    ) -> Result[T, F]:
        return Ok(self.unwrap()) if self.is_ok() else await fn(self.unwrap_err())


class Ok(Result[T, E]):
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

    LazyResult enables unified sync/async chaining - all methods accept
    both sync and async functions. The chain is not executed until
    `.collect()` is called.

    Example:
        result = await (
            LazyResult.from_awaitable(fetch_user(42))
            .and_then(fetch_profile)   # Async function
            .map(lambda p: p.name)     # Sync function
            .tee(print)                # Side effect
            .collect()
        )

    Or from an existing Result:
        result = await Ok(5).lazy().map(f).collect()
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

    def map(self, fn: Callable[[T], U]) -> LazyResult[U, E]:
        """Transform Ok value. fn can be sync or async."""
        return cast(LazyResult[U, E], self._chain(MapOp(fn)))

    def map_err(self, fn: Callable[[E], F]) -> LazyResult[T, F]:
        """Transform Err value. fn can be sync or async."""
        return cast(LazyResult[T, F], self._chain(MapErrOp(fn)))

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> LazyResult[U, E]:
        """Chain Result-returning function. fn can be sync or async."""
        return cast(LazyResult[U, E], self._chain(AndThenOp(fn)))

    def or_else(self, fn: Callable[[E], Result[T, F]]) -> LazyResult[T, F]:
        """Recover from Err. fn can be sync or async."""
        return cast(LazyResult[T, F], self._chain(OrElseOp(fn)))

    def tee(self, fn: Callable[[T], Any]) -> LazyResult[T, E]:
        """Side effect on Ok value. fn can be sync or async."""
        return cast(LazyResult[T, E], self._chain(TeeOp(fn)))

    inspect = tee

    def inspect_err(self, fn: Callable[[E], Any]) -> LazyResult[T, E]:
        """Side effect on Err value. fn can be sync or async."""
        return cast(LazyResult[T, E], self._chain(InspectErrOp(fn)))

    def flatten(self: LazyResult[Result[U, E], E]) -> LazyResult[U, E]:
        """Flatten nested LazyResult[Result[U, E], E] to LazyResult[U, E]."""
        return cast(LazyResult[U, E], self._chain(FlattenOp()))

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
    """Sequence Results into Result of list. Fails fast on first Err."""
    values: list[T] = []
    for r in results:
        if r.is_err():
            return Err(r.unwrap_err())
        values.append(r.unwrap())
    return Ok(values)


def traverse(items: Iterable[U], fn: Callable[[U], Result[T, E]]) -> Result[list[T], E]:
    """Map fn over items, sequence into Result. Fails fast on first Err."""
    return sequence(fn(item) for item in items)
