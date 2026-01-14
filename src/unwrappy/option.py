"""Option type for representing optional values.

This module provides a Rust-inspired Option type with Some and Nothing variants
for safe handling of optional values without relying on Python's None.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Coroutine, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Literal, NoReturn, TypeAlias, TypeVar, cast

from unwrappy.exceptions import UnwrapError

if TYPE_CHECKING:
    from typing_extensions import TypeIs

    from unwrappy.result import Err, Ok

T = TypeVar("T", covariant=True)  # Value type for Some
U = TypeVar("U")  # For transformations
E = TypeVar("E")  # For error types in ok_or conversions


class Some(Generic[T]):
    """Some variant of Option containing a value.

    Args:
        value: The value to wrap.

    Example:
        >>> option = Some(42)
        >>> option.unwrap()
        42
        >>> option.is_some()
        True
    """

    __slots__ = ("_value",)
    __match_args__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def __repr__(self) -> str:
        return f"Some({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Some) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Some", self._value))

    def is_some(self) -> Literal[True]:
        """Return True (this is Some)."""
        return True

    def is_nothing(self) -> Literal[False]:
        """Return False (this is not Nothing)."""
        return False

    def unwrap(self) -> T:
        """Return the Some value."""
        return self._value

    def unwrap_or(self, default: object) -> T:
        """Return the Some value, ignoring the default."""
        return self._value

    def unwrap_or_else(self, fn: Callable[[], U]) -> T:
        """Return the Some value, ignoring the function."""
        return self._value

    def unwrap_or_raise(self, exc: BaseException) -> T:
        """Return the Some value, ignoring the exception."""
        return self._value

    def expect(self, msg: str) -> T:
        """Return the Some value."""
        return self._value

    def expect_nothing(self, msg: str) -> NoReturn:
        """Raise UnwrapError with custom message (this is Some, not Nothing)."""
        raise UnwrapError(f"{msg}: {self._value!r}", self._value)

    def map(self, fn: Callable[[T], U]) -> Some[U]:
        """Transform the Some value."""
        return Some(fn(self._value))

    def map_or(self, default: U, fn: Callable[[T], U]) -> U:
        """Apply fn to the Some value."""
        return fn(self._value)

    def map_or_else(self, default_fn: Callable[[], U], fn: Callable[[T], U]) -> U:
        """Apply fn to the Some value."""
        return fn(self._value)

    def and_then(self, fn: Callable[[T], Some[U] | _NothingType]) -> Some[U] | _NothingType:
        """Chain Option-returning operation."""
        return fn(self._value)

    def or_else(self, fn: Callable[[], Some[U] | _NothingType]) -> Some[T]:
        """Return self (has value, no need to recover)."""
        return self

    def filter(self, predicate: Callable[[T], bool]) -> Some[T] | _NothingType:
        """Return Some if predicate passes, else Nothing."""
        if predicate(self._value):
            return self
        return NOTHING

    def tee(self, fn: Callable[[T], Any]) -> Some[T]:
        """Execute fn for side effects, return self."""
        fn(self._value)
        return self

    inspect = tee

    def inspect_nothing(self, fn: Callable[[], Any]) -> Some[T]:
        """Return self (not Nothing, skip fn)."""
        return self

    def flatten(self: Some[Some[U] | _NothingType]) -> Some[U] | _NothingType:
        """Flatten nested Option."""
        return self._value

    def to_tuple(self) -> tuple[T]:
        """Convert to single-element tuple."""
        return (self._value,)

    def zip(self, other: Some[U] | _NothingType) -> Some[tuple[T, U]] | _NothingType:
        """Zip with another Option."""
        if isinstance(other, Some):
            return Some((self._value, other.unwrap()))
        return NOTHING

    def zip_with(self, other: Some[U] | _NothingType, fn: Callable[[T, U], Any]) -> Some[Any] | _NothingType:
        """Zip with another Option using a combining function."""
        if isinstance(other, Some):
            return Some(fn(self._value, other.unwrap()))
        return NOTHING

    def xor(self, other: Some[U] | _NothingType) -> Some[T] | Some[U] | _NothingType:
        """Return Some if exactly one is Some, else Nothing."""
        if isinstance(other, _NothingType):
            return self
        return NOTHING

    def ok_or(self, err: E) -> Ok[T] | Err[E]:
        """Convert to Ok with the Some value."""
        from unwrappy.result import Ok

        return Ok(self._value)

    def ok_or_else(self, fn: Callable[[], E]) -> Ok[T] | Err[E]:
        """Convert to Ok with the Some value."""
        from unwrappy.result import Ok

        return Ok(self._value)

    def lazy(self) -> LazyOption[T]:
        """Convert to LazyOption for deferred chaining."""
        return LazyOption(self)

    async def map_async(self, fn: Callable[[T], Coroutine[Any, Any, U]]) -> Some[U]:
        """Transform Some value with async function."""
        return Some(await fn(self._value))

    async def and_then_async(
        self, fn: Callable[[T], Coroutine[Any, Any, Some[U] | _NothingType]]
    ) -> Some[U] | _NothingType:
        """Chain async Option-returning operation."""
        return await fn(self._value)

    async def or_else_async(self, fn: Callable[[], Coroutine[Any, Any, Some[U] | _NothingType]]) -> Some[T]:
        """Return self (has value, no need to recover)."""
        return self


class _NothingType:
    """Nothing variant of Option representing absence of value.

    This is a singleton class. Use the NOTHING constant.

    Example:
        >>> option = NOTHING
        >>> option.is_nothing()
        True
        >>> option.unwrap_or(0)
        0
    """

    __slots__ = ()
    __match_args__ = ()

    _instance: _NothingType | None = None

    def __new__(cls) -> _NothingType:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "Nothing"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NothingType)

    def __hash__(self) -> int:
        return hash("Nothing")

    def is_some(self) -> Literal[False]:
        """Return False (this is not Some)."""
        return False

    def is_nothing(self) -> Literal[True]:
        """Return True (this is Nothing)."""
        return True

    def unwrap(self) -> NoReturn:
        """Raise UnwrapError (no value in Nothing)."""
        raise UnwrapError("Called unwrap on Nothing", None)

    def unwrap_or(self, default: U) -> U:
        """Return the default value."""
        return default

    def unwrap_or_else(self, fn: Callable[[], U]) -> U:
        """Compute and return value from function."""
        return fn()

    def unwrap_or_raise(self, exc: BaseException) -> NoReturn:
        """Raise the provided exception."""
        raise exc

    def expect(self, msg: str) -> NoReturn:
        """Raise UnwrapError with custom message."""
        raise UnwrapError(msg, None)

    def expect_nothing(self, msg: str) -> None:
        """Return None (this is Nothing)."""
        return None

    def map(self, fn: Callable[[Any], U]) -> _NothingType:
        """Return self unchanged (no value to transform)."""
        return self

    def map_or(self, default: U, fn: Callable[[Any], U]) -> U:
        """Return the default value."""
        return default

    def map_or_else(self, default_fn: Callable[[], U], fn: Callable[[Any], U]) -> U:
        """Apply default_fn."""
        return default_fn()

    def and_then(self, fn: Callable[[Any], Some[U] | _NothingType]) -> _NothingType:
        """Return self (no value to chain)."""
        return self

    def or_else(self, fn: Callable[[], Some[U] | _NothingType]) -> Some[U] | _NothingType:
        """Recover from Nothing by calling fn."""
        return fn()

    def filter(self, predicate: Callable[[Any], bool]) -> _NothingType:
        """Return self (nothing to filter)."""
        return self

    def tee(self, fn: Callable[[Any], Any]) -> _NothingType:
        """Return self (no value to inspect)."""
        return self

    inspect = tee

    def inspect_nothing(self, fn: Callable[[], Any]) -> _NothingType:
        """Execute fn for side effects, return self."""
        fn()
        return self

    def flatten(self) -> _NothingType:
        """Return self (already flat)."""
        return self

    def to_tuple(self) -> tuple[None]:
        """Convert to tuple with None."""
        return (None,)

    def zip(self, other: Some[U] | _NothingType) -> _NothingType:
        """Return Nothing (can't zip with Nothing)."""
        return self

    def zip_with(self, other: Some[U] | _NothingType, fn: Callable[[Any, U], Any]) -> _NothingType:
        """Return Nothing (can't zip with Nothing)."""
        return self

    def xor(self, other: Some[U] | _NothingType) -> Some[U] | _NothingType:
        """Return other (Nothing xor X = X)."""
        return other

    def ok_or(self, err: E) -> Ok[Any] | Err[E]:
        """Convert to Err with the given error."""
        from unwrappy.result import Err

        return Err(err)

    def ok_or_else(self, fn: Callable[[], E]) -> Ok[Any] | Err[E]:
        """Convert to Err with computed error."""
        from unwrappy.result import Err

        return Err(fn())

    def lazy(self) -> LazyOption[Any]:
        """Convert to LazyOption for deferred chaining."""
        return LazyOption(self)

    async def map_async(self, fn: Callable[[Any], Coroutine[Any, Any, U]]) -> _NothingType:
        """Return self (no value to transform)."""
        return self

    async def and_then_async(self, fn: Callable[[Any], Coroutine[Any, Any, Some[U] | _NothingType]]) -> _NothingType:
        """Return self (no value to chain)."""
        return self

    async def or_else_async(
        self, fn: Callable[[], Coroutine[Any, Any, Some[U] | _NothingType]]
    ) -> Some[U] | _NothingType:
        """Recover from Nothing with async function."""
        return await fn()


NOTHING = _NothingType()
"""Nothing singleton object."""

Nothing: TypeAlias = _NothingType
"""Type alias for the Nothing type (for annotations)"""

Option: TypeAlias = Some[T] | _NothingType
"""Type alias for the union of Some and Nothing."""


@dataclass(frozen=True, slots=True)
class OptionMapOp:
    """Operation that transforms the Some value."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class OptionAndThenOp:
    """Operation that chains an Option-returning function on Some."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class OptionOrElseOp:
    """Operation that chains an Option-returning function on Nothing."""

    fn: Callable[[], Any]


@dataclass(frozen=True, slots=True)
class OptionFilterOp:
    """Operation that filters based on a predicate."""

    predicate: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class OptionTeeOp:
    """Operation that executes a side effect on Some."""

    fn: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class OptionInspectNothingOp:
    """Operation that executes a side effect on Nothing."""

    fn: Callable[[], Any]


@dataclass(frozen=True, slots=True)
class OptionFlattenOp:
    """Operation that flattens nested Option."""

    pass


OptionOperation = (
    OptionMapOp
    | OptionAndThenOp
    | OptionOrElseOp
    | OptionFilterOp
    | OptionTeeOp
    | OptionInspectNothingOp
    | OptionFlattenOp
)


async def _maybe_await_option(value: U | Awaitable[U]) -> U:
    """Await if awaitable, otherwise return as-is."""
    if inspect.isawaitable(value):
        return await value
    return cast(U, value)


class LazyOption(Generic[T]):
    """Lazy Option with deferred execution for clean async chaining.

    LazyOption builds a pipeline of operations that execute only when
    `.collect()` is called. All methods accept both sync and async
    functions transparently.

    Type Parameters:
        T: The value type.

    Example:
        >>> async def fetch_config(key: str) -> Option[str]: ...
        >>>
        >>> result = await (
        ...     LazyOption.from_awaitable(fetch_config("api_key"))
        ...     .map(str.upper)
        ...     .filter(lambda s: len(s) > 0)
        ...     .collect()
        ... )

    From an existing Option:
        >>> result = await Some(5).lazy().map(lambda x: x * 2).collect()
        >>> result
        Some(10)
    """

    __slots__ = ("_source", "_operations")

    def __init__(
        self,
        source: Awaitable[Some[T] | _NothingType] | Some[T] | _NothingType,
        operations: tuple[OptionOperation, ...] = (),
    ) -> None:
        self._source = source
        self._operations = operations

    @classmethod
    def some(cls, value: U) -> LazyOption[U]:
        """Create LazyOption from a value."""
        return LazyOption(Some(value))

    @classmethod
    def nothing(cls) -> LazyOption[Any]:
        """Create LazyOption from Nothing."""
        return LazyOption(NOTHING)

    @classmethod
    def from_option(cls, option: Some[T] | _NothingType) -> LazyOption[T]:
        """Create LazyOption from an existing Option."""
        return cls(option)

    @classmethod
    def from_awaitable(cls, awaitable: Awaitable[Some[T] | _NothingType]) -> LazyOption[T]:
        """Create LazyOption from a coroutine/awaitable that returns Option."""
        return cls(awaitable)

    def map(self, fn: Callable[[T], U | Awaitable[U]]) -> LazyOption[U]:
        """Transform Some value. fn can be sync or async."""
        return cast(LazyOption[U], LazyOption(self._source, (*self._operations, OptionMapOp(fn))))

    def and_then(
        self,
        fn: Callable[[T], Some[U] | _NothingType | Awaitable[Some[U] | _NothingType]],
    ) -> LazyOption[U]:
        """Chain Option-returning function. fn can be sync or async."""
        return cast(LazyOption[U], LazyOption(self._source, (*self._operations, OptionAndThenOp(fn))))

    def or_else(
        self,
        fn: Callable[[], Some[T] | _NothingType | Awaitable[Some[T] | _NothingType]],
    ) -> LazyOption[T]:
        """Recover from Nothing. fn can be sync or async."""
        return LazyOption(self._source, (*self._operations, OptionOrElseOp(fn)))

    def filter(self, predicate: Callable[[T], bool | Awaitable[bool]]) -> LazyOption[T]:
        """Filter based on predicate. predicate can be sync or async."""
        return LazyOption(self._source, (*self._operations, OptionFilterOp(predicate)))

    def tee(self, fn: Callable[[T], Any]) -> LazyOption[T]:
        """Side effect on Some value. fn can be sync or async."""
        return LazyOption(self._source, (*self._operations, OptionTeeOp(fn)))

    inspect = tee

    def inspect_nothing(self, fn: Callable[[], Any]) -> LazyOption[T]:
        """Side effect on Nothing. fn can be sync or async."""
        return LazyOption(self._source, (*self._operations, OptionInspectNothingOp(fn)))

    def flatten(self: LazyOption[Some[U] | _NothingType]) -> LazyOption[U]:
        """Flatten nested LazyOption[Option[U]] to LazyOption[U]."""
        return cast(LazyOption[U], LazyOption(self._source, (*self._operations, OptionFlattenOp())))

    async def collect(self) -> Some[T] | _NothingType:
        """Execute the lazy chain and return the final Option."""
        option: Some[Any] | _NothingType = await _maybe_await_option(self._source)

        for op in self._operations:
            option = await self._execute_op(option, op)

        return option

    async def _execute_op(self, option: Some[Any] | _NothingType, op: OptionOperation) -> Some[Any] | _NothingType:
        """Execute a single operation on an Option."""
        is_some = option.is_some()

        match op:
            case OptionMapOp(fn) if is_some:
                return Some(await _maybe_await_option(fn(option.unwrap())))

            case OptionAndThenOp(fn) if is_some:
                return await _maybe_await_option(fn(option.unwrap()))

            case OptionOrElseOp(fn) if not is_some:
                return await _maybe_await_option(fn())

            case OptionFilterOp(predicate) if is_some:
                if not await _maybe_await_option(predicate(option.unwrap())):
                    return NOTHING

            case OptionTeeOp(fn) if is_some:
                await _maybe_await_option(fn(option.unwrap()))

            case OptionInspectNothingOp(fn) if not is_some:
                await _maybe_await_option(fn())

            case OptionFlattenOp() if is_some:
                return option.unwrap()

        return option


def sequence_options(options: Iterable[Some[T] | _NothingType]) -> Some[list[T]] | _NothingType:
    """Collect an iterable of Options into an Option of list.

    Fails fast on the first Nothing encountered.
    If all Options are Some, returns Some containing a list of all values.

    Args:
        options: Iterable of Option values to collect.

    Returns:
        Some(list) if all are Some, otherwise Nothing.

    Example:
        >>> sequence_options([Some(1), Some(2), Some(3)])
        Some([1, 2, 3])
        >>> sequence_options([Some(1), NOTHING, Some(3)])
        Nothing
        >>> sequence_options([])
        Some([])
    """
    values: list[T] = []
    for opt in options:
        if opt.is_nothing():
            return NOTHING
        values.append(opt.unwrap())
    return Some(values)


def traverse_options(items: Iterable[U], fn: Callable[[U], Some[T] | _NothingType]) -> Some[list[T]] | _NothingType:
    """Map a function over items and collect Options.

    Equivalent to `sequence_options(map(fn, items))` but more efficient.
    Fails fast on the first Nothing encountered.

    Args:
        items: Iterable of items to process.
        fn: Function returning Option for each item.

    Returns:
        Some(list) if all succeed, otherwise Nothing.

    Example:
        >>> def safe_sqrt(x: float) -> Option[float]:
        ...     return Some(x ** 0.5) if x >= 0 else NOTHING
        >>> traverse_options([4, 9, 16], safe_sqrt)
        Some([2.0, 3.0, 4.0])
        >>> traverse_options([4, -1, 16], safe_sqrt)
        Nothing
    """
    return sequence_options(fn(item) for item in items)


def from_nullable(value: T | None) -> Some[T] | _NothingType:
    """Convert a nullable value to Option.

    Args:
        value: A value that may be None.

    Returns:
        Some(value) if value is not None, otherwise Nothing.

    Example:
        >>> from_nullable(42)
        Some(42)
        >>> from_nullable(None)
        Nothing
    """
    if value is None:
        return NOTHING
    return Some(value)


def is_some(option: Some[T] | _NothingType) -> TypeIs[Some[T]]:
    """Type guard to check if an option is Some.

    Unlike the `.is_some()` method, this standalone function enables
    proper type narrowing in conditional branches. This is necessary
    because Python's type system doesn't support narrowing based on
    method return types.

    Args:
        option: The Option to check.

    Returns:
        True if option is Some, with the type narrowed to Some[T].

    Example:
        >>> from unwrappy import Option, Some, Nothing, is_some
        >>> def get_value(opt: Option[int]) -> int:
        ...     if is_some(opt):
        ...         return opt.unwrap()  # Type checker knows opt is Some[int]
        ...     return 0
    """
    return isinstance(option, Some)


def is_nothing(option: Some[T] | _NothingType) -> TypeIs[_NothingType]:
    """Type guard to check if an option is Nothing.

    Unlike the `.is_nothing()` method, this standalone function enables
    proper type narrowing in conditional branches. This is necessary
    because Python's type system doesn't support narrowing based on
    method return types.

    Args:
        option: The Option to check.

    Returns:
        True if option is Nothing, with the type narrowed to _NothingType.

    Example:
        >>> from unwrappy import Option, Some, Nothing, is_nothing
        >>> def describe(opt: Option[int]) -> str:
        ...     if is_nothing(opt):
        ...         return "empty"  # Type checker knows opt is Nothing
        ...     return "has value"
    """
    return isinstance(option, _NothingType)
