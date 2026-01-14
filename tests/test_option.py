"""Comprehensive tests for the Option type."""

from __future__ import annotations

from typing import Literal

import pytest
from typing_extensions import assert_type

from unwrappy import NOTHING, Err, LazyOption, Ok, Option, Some
from unwrappy.exceptions import UnwrapError
from unwrappy.option import (
    _NothingType,
    from_nullable,
    sequence_options,
    traverse_options,
)


class TestSomeBasics:
    """Tests for Some variant basic behavior."""

    def test_some_is_some(self) -> None:
        assert Some(42).is_some() is True

    def test_some_is_nothing(self) -> None:
        assert Some(42).is_nothing() is False

    def test_some_unwrap(self) -> None:
        assert Some(42).unwrap() == 42

    def test_some_repr(self) -> None:
        assert repr(Some(42)) == "Some(42)"
        assert repr(Some("hello")) == "Some('hello')"

    def test_some_eq_same_value(self) -> None:
        assert Some(1) == Some(1)
        assert Some("hello") == Some("hello")

    def test_some_eq_different_value(self) -> None:
        assert Some(1) != Some(2)

    def test_some_eq_different_type(self) -> None:
        assert Some(1) != "Some(1)"
        assert Some(1) != 1

    def test_some_eq_vs_nothing(self) -> None:
        assert Some(1) != NOTHING

    def test_some_hash(self) -> None:
        assert hash(Some(1)) == hash(Some(1))
        assert hash(Some(1)) != hash(Some(2))
        # Can be used in sets
        s = {Some(1), Some(1), Some(2)}
        assert len(s) == 2


class TestNothingBasics:
    """Tests for Nothing variant basic behavior."""

    def test_nothing_is_some(self) -> None:
        assert NOTHING.is_some() is False

    def test_nothing_is_nothing(self) -> None:
        assert NOTHING.is_nothing() is True

    def test_nothing_unwrap_raises(self) -> None:
        with pytest.raises(UnwrapError) as exc_info:
            NOTHING.unwrap()
        assert exc_info.value.value is None

    def test_nothing_repr(self) -> None:
        assert repr(NOTHING) == "Nothing"

    def test_nothing_is_singleton(self) -> None:
        assert _NothingType() is NOTHING
        assert _NothingType() is _NothingType()

    def test_nothing_eq(self) -> None:
        assert NOTHING == NOTHING
        assert NOTHING == _NothingType()

    def test_nothing_hashable(self) -> None:
        s = {NOTHING, NOTHING}
        assert len(s) == 1
        assert hash(NOTHING) == hash(NOTHING)


class TestUnwrapMethods:
    """Tests for unwrap_or, unwrap_or_else, unwrap_or_raise, expect, expect_nothing."""

    def test_unwrap_or_on_some(self) -> None:
        assert Some(5).unwrap_or(0) == 5

    def test_unwrap_or_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.unwrap_or(0) == 0

    def test_unwrap_or_else_on_some(self) -> None:
        assert Some(5).unwrap_or_else(lambda: 0) == 5

    def test_unwrap_or_else_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.unwrap_or_else(lambda: 42) == 42

    def test_expect_on_some(self) -> None:
        assert Some(5).expect("should not fail") == 5

    def test_expect_on_nothing_raises(self) -> None:
        with pytest.raises(UnwrapError) as exc_info:
            NOTHING.expect("custom message")
        assert "custom message" in str(exc_info.value)
        assert exc_info.value.value is None

    def test_expect_nothing_on_nothing(self) -> None:
        assert NOTHING.expect_nothing("should not fail") is None

    def test_expect_nothing_on_some_raises(self) -> None:
        with pytest.raises(UnwrapError) as exc_info:
            Some(5).expect_nothing("custom message")
        assert "custom message" in str(exc_info.value)
        assert "5" in str(exc_info.value)
        assert exc_info.value.value == 5

    def test_unwrap_or_raise_on_some(self) -> None:
        assert Some(5).unwrap_or_raise(ValueError("error")) == 5

    def test_unwrap_or_raise_on_nothing(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            NOTHING.unwrap_or_raise(ValueError("no value"))
        assert str(exc_info.value) == "no value"


class TestMapCombinators:
    """Tests for map, map_or, map_or_else."""

    def test_map_on_some(self) -> None:
        assert Some(2).map(lambda x: x * 2) == Some(4)

    def test_map_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.map(lambda x: x * 2) is NOTHING

    def test_map_or_on_some(self) -> None:
        assert Some(2).map_or(0, lambda x: x * 2) == 4

    def test_map_or_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.map_or(0, lambda x: x * 2) == 0

    def test_map_or_else_on_some(self) -> None:
        assert Some(2).map_or_else(lambda: -1, lambda x: x * 2) == 4

    def test_map_or_else_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.map_or_else(lambda: -1, lambda x: x * 2) == -1


class TestChainCombinators:
    """Tests for and_then and or_else."""

    def test_and_then_on_some_returns_some(self) -> None:
        result = Some(2).and_then(lambda x: Some(x * 2))
        assert result == Some(4)

    def test_and_then_on_some_returns_nothing(self) -> None:
        result = Some(2).and_then(lambda x: NOTHING)
        assert result is NOTHING

    def test_and_then_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.and_then(lambda x: Some(x * 2)) is NOTHING

    def test_or_else_on_some(self) -> None:
        option: Option[int] = Some(5)
        assert option.or_else(lambda: Some(0)) == Some(5)

    def test_or_else_on_nothing_returns_some(self) -> None:
        option: Option[int] = NOTHING
        assert option.or_else(lambda: Some(42)) == Some(42)

    def test_or_else_on_nothing_returns_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.or_else(lambda: NOTHING) is NOTHING


class TestFilter:
    """Tests for filter method."""

    def test_filter_some_passes(self) -> None:
        assert Some(4).filter(lambda x: x > 0) == Some(4)

    def test_filter_some_fails(self) -> None:
        assert Some(-1).filter(lambda x: x > 0) is NOTHING

    def test_filter_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.filter(lambda x: x > 0) is NOTHING


class TestInspect:
    """Tests for tee/inspect and inspect_nothing."""

    def test_tee_on_some(self) -> None:
        captured: list[int] = []
        result = Some(5).tee(lambda x: captured.append(x))
        assert result == Some(5)
        assert captured == [5]

    def test_tee_on_nothing(self) -> None:
        captured: list[int] = []
        option: Option[int] = NOTHING
        result = option.tee(lambda x: captured.append(x))
        assert result is NOTHING
        assert captured == []

    def test_inspect_alias(self) -> None:
        captured: list[int] = []
        result = Some(5).inspect(lambda x: captured.append(x))
        assert result == Some(5)
        assert captured == [5]

    def test_inspect_nothing_on_nothing(self) -> None:
        called = []
        result = NOTHING.inspect_nothing(lambda: called.append(True))
        assert result is NOTHING
        assert called == [True]

    def test_inspect_nothing_on_some(self) -> None:
        called = []
        result = Some(5).inspect_nothing(lambda: called.append(True))
        assert result == Some(5)
        assert called == []


class TestFlatten:
    """Tests for flatten method."""

    def test_flatten_nested_some(self) -> None:
        nested: Some[Some[int] | _NothingType] = Some(Some(42))
        assert nested.flatten() == Some(42)

    def test_flatten_some_nothing(self) -> None:
        nested: Some[Some[int] | _NothingType] = Some(NOTHING)
        assert nested.flatten() is NOTHING

    def test_flatten_nothing(self) -> None:
        assert NOTHING.flatten() is NOTHING


class TestToTuple:
    """Tests for to_tuple method."""

    def test_to_tuple_on_some(self) -> None:
        assert Some(42).to_tuple() == (42,)

    def test_to_tuple_on_nothing(self) -> None:
        assert NOTHING.to_tuple() == (None,)


class TestZip:
    """Tests for zip and zip_with."""

    def test_zip_some_some(self) -> None:
        assert Some(1).zip(Some("a")) == Some((1, "a"))

    def test_zip_some_nothing(self) -> None:
        assert Some(1).zip(NOTHING) is NOTHING

    def test_zip_nothing_some(self) -> None:
        option: Option[int] = NOTHING
        assert option.zip(Some("a")) is NOTHING

    def test_zip_nothing_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.zip(NOTHING) is NOTHING

    def test_zip_with_some_some(self) -> None:
        assert Some(2).zip_with(Some(3), lambda a, b: a + b) == Some(5)

    def test_zip_with_some_nothing(self) -> None:
        assert Some(2).zip_with(NOTHING, lambda a, b: a + b) is NOTHING

    def test_zip_with_nothing_some(self) -> None:
        option: Option[int] = NOTHING
        assert option.zip_with(Some(3), lambda a, b: a + b) is NOTHING


class TestXor:
    """Tests for xor method."""

    def test_xor_some_some(self) -> None:
        assert Some(1).xor(Some(2)) is NOTHING

    def test_xor_some_nothing(self) -> None:
        assert Some(1).xor(NOTHING) == Some(1)

    def test_xor_nothing_some(self) -> None:
        option: Option[int] = NOTHING
        assert option.xor(Some(2)) == Some(2)

    def test_xor_nothing_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.xor(NOTHING) is NOTHING


class TestOkOr:
    """Tests for ok_or and ok_or_else."""

    def test_ok_or_on_some(self) -> None:
        assert Some(5).ok_or("error") == Ok(5)

    def test_ok_or_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.ok_or("error") == Err("error")

    def test_ok_or_else_on_some(self) -> None:
        assert Some(5).ok_or_else(lambda: "error") == Ok(5)

    def test_ok_or_else_on_nothing(self) -> None:
        option: Option[int] = NOTHING
        assert option.ok_or_else(lambda: "computed error") == Err("computed error")


class TestPatternMatching:
    """Tests for pattern matching via __match_args__."""

    def test_match_some(self) -> None:
        option: Option[int] = Some(42)
        match option:
            case Some(value):
                assert value == 42
            case _:
                pytest.fail("Should have matched Some")

    def test_match_nothing(self) -> None:
        option: Option[int] = NOTHING
        match option:
            case Some(_):
                pytest.fail("Should have matched Nothing")
            case _NothingType():
                pass  # Expected


class TestFromNullable:
    """Tests for from_nullable helper."""

    def test_from_nullable_value(self) -> None:
        assert from_nullable(42) == Some(42)

    def test_from_nullable_none(self) -> None:
        assert from_nullable(None) is NOTHING

    def test_from_nullable_zero(self) -> None:
        # Zero should be Some, not Nothing
        assert from_nullable(0) == Some(0)

    def test_from_nullable_empty_string(self) -> None:
        # Empty string should be Some, not Nothing
        assert from_nullable("") == Some("")

    def test_from_nullable_false(self) -> None:
        # False should be Some, not Nothing
        assert from_nullable(False) == Some(False)


class TestSequenceOptions:
    """Tests for sequence_options and traverse_options."""

    def test_sequence_all_some(self) -> None:
        options = [Some(1), Some(2), Some(3)]
        assert sequence_options(options) == Some([1, 2, 3])

    def test_sequence_with_nothing(self) -> None:
        options: list[Option[int]] = [Some(1), NOTHING, Some(3)]
        assert sequence_options(options) is NOTHING

    def test_sequence_empty(self) -> None:
        assert sequence_options([]) == Some([])

    def test_sequence_fails_fast(self) -> None:
        # The NOTHING should be encountered before we process all items
        def gen() -> list[Some[int] | _NothingType]:
            return [Some(1), NOTHING, Some(3)]

        assert sequence_options(gen()) is NOTHING

    def test_traverse_all_some(self) -> None:
        items = [1, 2, 3]
        result = traverse_options(items, lambda x: Some(x * 2))
        assert result == Some([2, 4, 6])

    def test_traverse_with_nothing(self) -> None:
        items = [1, 2, 3]

        def maybe_fail(x: int) -> Some[int] | _NothingType:
            if x == 2:
                return NOTHING
            return Some(x * 2)

        assert traverse_options(items, maybe_fail) is NOTHING

    def test_traverse_empty(self) -> None:
        result = traverse_options([], lambda x: Some(x))
        assert result == Some([])


class TestAsyncMethods:
    """Tests for async Option methods."""

    @pytest.mark.asyncio
    async def test_map_async_on_some(self) -> None:
        async def double(x: int) -> int:
            return x * 2

        result = await Some(5).map_async(double)
        assert result == Some(10)

    @pytest.mark.asyncio
    async def test_map_async_on_nothing(self) -> None:
        async def double(x: int) -> int:
            return x * 2

        option: Option[int] = NOTHING
        result = await option.map_async(double)
        assert result is NOTHING

    @pytest.mark.asyncio
    async def test_and_then_async_on_some(self) -> None:
        async def maybe_double(x: int) -> Some[int] | _NothingType:
            return Some(x * 2) if x > 0 else NOTHING

        result = await Some(5).and_then_async(maybe_double)
        assert result == Some(10)

    @pytest.mark.asyncio
    async def test_and_then_async_on_nothing(self) -> None:
        async def maybe_double(x: int) -> Some[int] | _NothingType:
            return Some(x * 2)

        option: Option[int] = NOTHING
        result = await option.and_then_async(maybe_double)
        assert result is NOTHING

    @pytest.mark.asyncio
    async def test_or_else_async_on_some(self) -> None:
        async def recover() -> Some[int] | _NothingType:
            return Some(42)

        result = await Some(5).or_else_async(recover)
        assert result == Some(5)

    @pytest.mark.asyncio
    async def test_or_else_async_on_nothing(self) -> None:
        async def recover() -> Some[int] | _NothingType:
            return Some(42)

        option: Option[int] = NOTHING
        result = await option.or_else_async(recover)
        assert result == Some(42)


class TestLazyOption:
    """Tests for LazyOption."""

    @pytest.mark.asyncio
    async def test_lazy_some_map(self) -> None:
        result = await LazyOption.some(5).map(lambda x: x * 2).collect()
        assert result == Some(10)

    @pytest.mark.asyncio
    async def test_lazy_nothing_map_skips(self) -> None:
        result = await LazyOption.nothing().map(lambda x: x * 2).collect()
        assert result is NOTHING

    @pytest.mark.asyncio
    async def test_lazy_and_then(self) -> None:
        result = await LazyOption.some(5).and_then(lambda x: Some(x * 2)).collect()
        assert result == Some(10)

    @pytest.mark.asyncio
    async def test_lazy_or_else(self) -> None:
        result = await LazyOption.nothing().or_else(lambda: Some(42)).collect()
        assert result == Some(42)

    @pytest.mark.asyncio
    async def test_lazy_filter_passes(self) -> None:
        result = await LazyOption.some(5).filter(lambda x: x > 3).collect()
        assert result == Some(5)

    @pytest.mark.asyncio
    async def test_lazy_filter_fails(self) -> None:
        result = await LazyOption.some(2).filter(lambda x: x > 3).collect()
        assert result is NOTHING

    @pytest.mark.asyncio
    async def test_lazy_tee(self) -> None:
        captured: list[int] = []
        result = await LazyOption.some(5).tee(lambda x: captured.append(x)).collect()
        assert result == Some(5)
        assert captured == [5]

    @pytest.mark.asyncio
    async def test_lazy_inspect_nothing(self) -> None:
        called: list[bool] = []
        result = await LazyOption.nothing().inspect_nothing(lambda: called.append(True)).collect()
        assert result is NOTHING
        assert called == [True]

    @pytest.mark.asyncio
    async def test_lazy_flatten(self) -> None:
        result = await LazyOption.some(Some(42)).flatten().collect()
        assert result == Some(42)

    @pytest.mark.asyncio
    async def test_lazy_complex_chain(self) -> None:
        result = await LazyOption.some(5).map(lambda x: x * 2).filter(lambda x: x > 5).map(str).collect()
        assert result == Some("10")

    @pytest.mark.asyncio
    async def test_lazy_from_option(self) -> None:
        result = await LazyOption.from_option(Some(42)).map(lambda x: x + 1).collect()
        assert result == Some(43)

    @pytest.mark.asyncio
    async def test_lazy_from_awaitable(self) -> None:
        async def get_option() -> Some[int] | _NothingType:
            return Some(42)

        result = await LazyOption.from_awaitable(get_option()).map(lambda x: x + 1).collect()
        assert result == Some(43)

    @pytest.mark.asyncio
    async def test_lazy_with_async_map(self) -> None:
        async def async_double(x: int) -> int:
            return x * 2

        result = await LazyOption.some(5).map(async_double).collect()
        assert result == Some(10)

    @pytest.mark.asyncio
    async def test_lazy_with_async_and_then(self) -> None:
        async def async_maybe_double(x: int) -> Some[int] | _NothingType:
            return Some(x * 2) if x > 0 else NOTHING

        result = await LazyOption.some(5).and_then(async_maybe_double).collect()
        assert result == Some(10)


class TestLazyMethod:
    """Tests for the .lazy() method on Some and Nothing."""

    @pytest.mark.asyncio
    async def test_some_lazy(self) -> None:
        result = await Some(5).lazy().map(lambda x: x * 2).collect()
        assert result == Some(10)

    @pytest.mark.asyncio
    async def test_nothing_lazy(self) -> None:
        result = await NOTHING.lazy().map(lambda x: x * 2).collect()
        assert result is NOTHING


class TestTypeInference:
    """Tests for type inference using assert_type."""

    def test_some_type(self) -> None:
        some: Some[int] = Some(42)
        assert_type(some, Some[int])

    def test_is_some_literal_true(self) -> None:
        some: Some[int] = Some(42)
        is_some = some.is_some()
        assert_type(is_some, Literal[True])

    def test_is_nothing_literal_false_on_some(self) -> None:
        some: Some[int] = Some(42)
        is_nothing = some.is_nothing()
        assert_type(is_nothing, Literal[False])

    def test_is_some_literal_false_on_nothing(self) -> None:
        is_some = NOTHING.is_some()
        assert_type(is_some, Literal[False])

    def test_is_nothing_literal_true(self) -> None:
        is_nothing = NOTHING.is_nothing()
        assert_type(is_nothing, Literal[True])


class TestEdgeCases:
    """Tests for edge cases and special values."""

    def test_some_with_none_value(self) -> None:
        # Some can contain Python's None as a value
        option = Some(None)
        assert option.is_some() is True
        assert option.unwrap() is None

    def test_some_with_false_value(self) -> None:
        option = Some(False)
        assert option.is_some() is True
        assert option.unwrap() is False

    def test_some_with_zero_value(self) -> None:
        option = Some(0)
        assert option.is_some() is True
        assert option.unwrap() == 0

    def test_some_with_empty_string(self) -> None:
        option = Some("")
        assert option.is_some() is True
        assert option.unwrap() == ""

    def test_some_with_empty_list(self) -> None:
        option = Some([])
        assert option.is_some() is True
        assert option.unwrap() == []

    def test_nested_some(self) -> None:
        option = Some(Some(42))
        assert option.is_some() is True
        inner = option.unwrap()
        assert isinstance(inner, Some)
        assert inner.unwrap() == 42
