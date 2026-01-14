"""Comprehensive tests for the Result type."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from typing_extensions import assert_type

from unwrappy import LazyResult
from unwrappy.exceptions import UnwrapError
from unwrappy.result import Err, Ok, Result, sequence_results, traverse_results


class TestOkBasics:
    """Tests for Ok variant basic behavior."""

    def test_ok_is_ok(self) -> None:
        assert Ok(42).is_ok() is True

    def test_ok_is_err(self) -> None:
        assert Ok(42).is_err() is False

    def test_ok_unwrap(self) -> None:
        assert Ok(42).unwrap() == 42

    def test_ok_unwrap_err_raises(self) -> None:
        with pytest.raises(UnwrapError) as exc_info:
            Ok(42).unwrap_err()
        assert exc_info.value.value == 42

    def test_ok_repr(self) -> None:
        assert repr(Ok(42)) == "Ok(42)"
        assert repr(Ok("hello")) == "Ok('hello')"

    def test_ok_eq_same_value(self) -> None:
        assert Ok(1) == Ok(1)
        assert Ok("hello") == Ok("hello")

    def test_ok_eq_different_value(self) -> None:
        assert Ok(1) != Ok(2)

    def test_ok_eq_different_type(self) -> None:
        assert Ok(1) != "Ok(1)"
        assert Ok(1) != 1

    def test_ok_eq_vs_err(self) -> None:
        assert Ok(1) != Err(1)


class TestErrBasics:
    """Tests for Err variant basic behavior."""

    def test_err_is_ok(self) -> None:
        assert Err("error").is_ok() is False

    def test_err_is_err(self) -> None:
        assert Err("error").is_err() is True

    def test_err_unwrap_raises(self) -> None:
        with pytest.raises(UnwrapError) as exc_info:
            Err("my error").unwrap()
        assert exc_info.value.value == "my error"

    def test_err_unwrap_err(self) -> None:
        assert Err("my error").unwrap_err() == "my error"

    def test_err_repr(self) -> None:
        assert repr(Err("fail")) == "Err('fail')"
        assert repr(Err(42)) == "Err(42)"

    def test_err_eq_same_error(self) -> None:
        assert Err("x") == Err("x")
        assert Err(42) == Err(42)

    def test_err_eq_different_error(self) -> None:
        assert Err("x") != Err("y")


class TestUnwrapMethods:
    """Tests for unwrap_or, unwrap_or_else, unwrap_or_raise, expect, expect_err."""

    def test_unwrap_or_on_ok(self) -> None:
        assert Ok(5).unwrap_or(0) == 5

    def test_unwrap_or_on_err(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.unwrap_or(0) == 0

    def test_unwrap_or_else_on_ok(self) -> None:
        assert Ok(5).unwrap_or_else(lambda e: len(e)) == 5

    def test_unwrap_or_else_on_err(self) -> None:
        result: Result[int, str] = Err("abc")
        assert result.unwrap_or_else(len) == 3

    def test_expect_on_ok(self) -> None:
        assert Ok(5).expect("should not fail") == 5

    def test_expect_on_err_raises(self) -> None:
        result: Result[int, str] = Err("error value")
        with pytest.raises(UnwrapError) as exc_info:
            result.expect("custom message")
        assert "custom message" in str(exc_info.value)
        assert "error value" in str(exc_info.value)
        assert exc_info.value.value == "error value"

    def test_expect_err_on_err(self) -> None:
        assert Err("error").expect_err("should not fail") == "error"

    def test_expect_err_on_ok_raises(self) -> None:
        with pytest.raises(UnwrapError) as exc_info:
            Ok(5).expect_err("custom message")
        assert "custom message" in str(exc_info.value)
        assert "5" in str(exc_info.value)
        assert exc_info.value.value == 5

    def test_unwrap_or_raise_on_ok(self) -> None:
        assert Ok(5).unwrap_or_raise(lambda e: ValueError(str(e))) == 5

    def test_unwrap_or_raise_on_err(self) -> None:
        result: Result[int, str] = Err("bad input")
        with pytest.raises(ValueError) as exc_info:
            result.unwrap_or_raise(lambda e: ValueError(f"Invalid: {e}"))
        assert str(exc_info.value) == "Invalid: bad input"

    def test_unwrap_or_raise_http_pattern(self) -> None:
        """Practical example: mapping domain errors to HTTP exceptions."""

        class HTTPException(Exception):
            def __init__(self, status: int, detail: str) -> None:
                self.status = status
                self.detail = detail
                super().__init__(detail)

        class NotFoundError:
            def __init__(self, resource: str) -> None:
                self.resource = resource

        def to_http(e: NotFoundError) -> HTTPException:
            return HTTPException(404, f"{e.resource} not found")

        result: Result[str, NotFoundError] = Err(NotFoundError("User"))
        with pytest.raises(HTTPException) as exc_info:
            result.unwrap_or_raise(to_http)
        assert exc_info.value.status == 404
        assert exc_info.value.detail == "User not found"


class TestAccessorMethods:
    """Tests for ok() and err() accessor methods returning Option."""

    def test_ok_method_on_ok(self) -> None:
        from unwrappy import Some

        assert Ok(5).ok() == Some(5)

    def test_ok_method_on_err(self) -> None:
        from unwrappy import NOTHING

        result: Result[int, str] = Err("error")
        assert result.ok() is NOTHING

    def test_err_method_on_ok(self) -> None:
        from unwrappy import NOTHING

        assert Ok(5).err() is NOTHING

    def test_err_method_on_err(self) -> None:
        from unwrappy import Some

        assert Err("error").err() == Some("error")

    def test_ok_method_distinguishes_none_value(self) -> None:
        """Test that Ok(None).ok() returns Some(None), not Nothing."""
        from unwrappy import NOTHING, Some

        # This is the key improvement: we can now distinguish
        # Ok(None) from Err(x) via ok()
        assert Ok(None).ok() == Some(None)
        assert Ok(None).ok() is not NOTHING


class TestMapCombinators:
    """Tests for map, map_or, map_or_else, map_err."""

    def test_map_on_ok(self) -> None:
        assert Ok(2).map(lambda x: x * 2) == Ok(4)

    def test_map_on_err(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.map(lambda x: x * 2) == Err("error")

    def test_map_or_on_ok(self) -> None:
        assert Ok(2).map_or(0, lambda x: x * 2) == 4

    def test_map_or_on_err(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.map_or(0, lambda x: x * 2) == 0

    def test_map_or_else_on_ok(self) -> None:
        assert Ok(2).map_or_else(len, lambda x: x * 2) == 4

    def test_map_or_else_on_err(self) -> None:
        result: Result[int, str] = Err("abc")
        assert result.map_or_else(len, lambda x: x * 2) == 3

    def test_map_err_on_ok(self) -> None:
        result: Result[int, str] = Ok(5)
        assert result.map_err(str.upper) == Ok(5)

    def test_map_err_on_err(self) -> None:
        result: Result[int, str] = Err("err")
        assert result.map_err(str.upper) == Err("ERR")


class TestChainCombinators:
    """Tests for and_then and or_else."""

    def test_and_then_on_ok_returns_ok(self) -> None:
        result = Ok(2).and_then(lambda x: Ok(x * 2))
        assert result == Ok(4)

    def test_and_then_on_ok_returns_err(self) -> None:
        result = Ok(2).and_then(lambda x: Err("fail"))
        assert result == Err("fail")

    def test_and_then_on_err(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.and_then(lambda x: Ok(x * 2)) == Err("error")

    def test_or_else_on_ok(self) -> None:
        result: Result[int, str] = Ok(5)
        assert result.or_else(lambda e: Ok(0)) == Ok(5)

    def test_or_else_on_err_returns_ok(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.or_else(lambda e: Ok(0)) == Ok(0)

    def test_or_else_on_err_returns_err(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.or_else(lambda e: Err("new error")) == Err("new error")


class TestAsyncCombinators:
    """Tests for async map, map_err, and_then, or_else."""

    async def test_map_async_on_ok(self) -> None:
        async def async_double(x: int) -> int:
            return x * 2

        result = await Ok(2).map_async(async_double)
        assert result == Ok(4)

    async def test_map_async_on_err(self) -> None:
        async def async_double(x: int) -> int:
            return x * 2

        result: Result[int, str] = Err("error")
        assert await result.map_async(async_double) == Err("error")

    async def test_map_err_async_on_ok(self) -> None:
        async def async_upper(s: str) -> str:
            return s.upper()

        result: Result[int, str] = Ok(5)
        assert await result.map_err_async(async_upper) == Ok(5)

    async def test_map_err_async_on_err(self) -> None:
        async def async_upper(s: str) -> str:
            return s.upper()

        result: Result[int, str] = Err("error")
        assert await result.map_err_async(async_upper) == Err("ERROR")

    async def test_and_then_async_on_ok(self) -> None:
        async def async_double_result(x: int) -> Result[int, str]:
            return Ok(x * 2)

        result = await Ok(2).and_then_async(async_double_result)
        assert result == Ok(4)

    async def test_and_then_async_on_ok_returns_err(self) -> None:
        async def async_fail(x: int) -> Result[int, str]:
            return Err("async fail")

        result = await Ok(2).and_then_async(async_fail)
        assert result == Err("async fail")

    async def test_and_then_async_on_err(self) -> None:
        async def async_double_result(x: int) -> Result[int, str]:
            return Ok(x * 2)

        result: Result[int, str] = Err("error")
        assert await result.and_then_async(async_double_result) == Err("error")

    async def test_or_else_async_on_ok(self) -> None:
        async def async_recover(e: str) -> Result[int, str]:
            return Ok(0)

        result: Result[int, str] = Ok(5)
        assert await result.or_else_async(async_recover) == Ok(5)

    async def test_or_else_async_on_err_returns_ok(self) -> None:
        async def async_recover(e: str) -> Result[int, str]:
            return Ok(len(e))

        result: Result[int, str] = Err("error")
        assert await result.or_else_async(async_recover) == Ok(5)

    async def test_or_else_async_on_err_returns_err(self) -> None:
        async def async_fail(e: str) -> Result[int, str]:
            return Err(f"new: {e}")

        result: Result[int, str] = Err("error")
        assert await result.or_else_async(async_fail) == Err("new: error")


class TestPatternMatching:
    """Tests for pattern matching via __match_args__."""

    def test_match_ok(self) -> None:
        result: Result[int, str] = Ok(42)
        match result:
            case Ok(value):
                assert value == 42
            case Err(_):
                pytest.fail("Should have matched Ok")

    def test_match_err(self) -> None:
        result: Result[int, str] = Err("error")
        match result:
            case Ok(_):
                pytest.fail("Should have matched Err")
            case Err(error):
                assert error == "error"

    def test_match_exhaustive(self) -> None:
        def process(result: Result[int, str]) -> str:
            match result:
                case Ok(value):
                    return f"success: {value}"
                case Err(error):
                    return f"failure: {error}"
            raise AssertionError("unreachable")

        assert process(Ok(42)) == "success: 42"
        assert process(Err("oops")) == "failure: oops"


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_ok_with_none_value(self) -> None:
        from unwrappy import Some

        result = Ok(None)
        assert result.is_ok() is True
        assert result.unwrap() is None
        assert result.ok() == Some(None)  # Returns Some(None), not Nothing
        assert repr(result) == "Ok(None)"

    def test_err_with_none_error(self) -> None:
        from unwrappy import Some

        result = Err(None)
        assert result.is_err() is True
        assert result.unwrap_err() is None
        assert result.err() == Some(None)  # Returns Some(None), not Nothing
        assert repr(result) == "Err(None)"

    def test_ok_with_callable_value(self) -> None:
        fn = lambda: 42  # noqa: E731
        result = Ok(fn)
        assert result.is_ok() is True
        assert result.unwrap()() == 42

    def test_nested_result(self) -> None:
        inner: Result[int, str] = Ok(42)
        outer: Result[Result[int, str], str] = Ok(inner)

        assert outer.is_ok() is True
        assert outer.unwrap() == Ok(42)
        assert outer.unwrap().unwrap() == 42

    def test_ok_with_complex_object(self) -> None:
        @dataclass
        class User:
            name: str
            age: int

        user = User("Alice", 30)
        result = Ok(user)

        assert result.is_ok() is True
        assert result.unwrap().name == "Alice"
        assert result.unwrap().age == 30

    def test_map_changes_type(self) -> None:
        result = Ok("hello").map(len)
        assert result == Ok(5)
        assert isinstance(result.unwrap(), int)

    def test_chained_operations(self) -> None:
        def parse_int(s: str) -> Result[int, str]:
            try:
                return Ok(int(s))
            except ValueError:
                return Err(f"Cannot parse '{s}' as int")

        def validate_positive(n: int) -> Result[int, str]:
            if n > 0:
                return Ok(n)
            return Err("Number must be positive")

        # Success chain
        result = parse_int("42").and_then(validate_positive).map(lambda x: x * 2)
        assert result == Ok(84)

        # Fail at parse
        result = parse_int("abc").and_then(validate_positive).map(lambda x: x * 2)
        assert result == Err("Cannot parse 'abc' as int")

        # Fail at validate
        result = parse_int("-5").and_then(validate_positive).map(lambda x: x * 2)
        assert result == Err("Number must be positive")

    def test_map_err_then_or_else(self) -> None:
        result: Result[int, str] = Err("error")
        recovered = result.map_err(str.upper).or_else(lambda e: Ok(len(e)))
        assert recovered == Ok(5)  # len("ERROR") == 5


class TestUnwrapError:
    """Tests for UnwrapError exception."""

    def test_unwrap_error_has_value_attribute_on_ok_unwrap_err(self) -> None:
        try:
            Ok(42).unwrap_err()
        except UnwrapError as e:
            assert e.value == 42

    def test_unwrap_error_has_value_attribute_on_err_unwrap(self) -> None:
        try:
            Err("my error").unwrap()
        except UnwrapError as e:
            assert e.value == "my error"

    def test_unwrap_error_message_format_expect(self) -> None:
        result: Result[int, str] = Err("detailed error")
        try:
            result.expect("Operation failed")
        except UnwrapError as e:
            message = str(e)
            assert "Operation failed" in message
            assert "detailed error" in message

    def test_unwrap_error_message_format_expect_err(self) -> None:
        try:
            Ok(123).expect_err("Expected error")
        except UnwrapError as e:
            message = str(e)
            assert "Expected error" in message
            assert "123" in message


class TestTeeInspect:
    """Tests for tee, inspect, and inspect_err methods."""

    def test_tee_on_ok_calls_fn(self) -> None:
        called_with: list[int] = []
        Ok(42).tee(lambda x: called_with.append(x))
        assert called_with == [42]

    def test_tee_on_ok_returns_self(self) -> None:
        result = Ok(42)
        assert result.tee(lambda x: None) is result

    def test_tee_on_err_skips_fn(self) -> None:
        called = False

        def should_not_call(x: int) -> None:
            nonlocal called
            called = True

        result: Result[int, str] = Err("error")
        result.tee(should_not_call)
        assert called is False

    def test_tee_on_err_returns_self(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.tee(lambda x: None) is result

    def test_inspect_is_alias_for_tee(self) -> None:
        # Both Ok and Err have inspect as alias for tee
        assert Ok.inspect is Ok.tee
        assert Err.inspect is Err.tee

    def test_inspect_err_on_err_calls_fn(self) -> None:
        called_with: list[str] = []
        result: Result[int, str] = Err("error")
        result.inspect_err(lambda e: called_with.append(e))
        assert called_with == ["error"]

    def test_inspect_err_on_err_returns_self(self) -> None:
        result: Result[int, str] = Err("error")
        assert result.inspect_err(lambda e: None) is result

    def test_inspect_err_on_ok_skips_fn(self) -> None:
        called = False

        def should_not_call(e: str) -> None:
            nonlocal called
            called = True

        Ok(42).inspect_err(should_not_call)
        assert called is False

    def test_inspect_err_on_ok_returns_self(self) -> None:
        result = Ok(42)
        assert result.inspect_err(lambda e: None) is result

    def test_tee_chains_nicely(self) -> None:
        log: list[str] = []
        result = (
            Ok(5)
            .tee(lambda x: log.append(f"got {x}"))
            .map(lambda x: x * 2)
            .tee(lambda x: log.append(f"doubled to {x}"))
        )
        assert result == Ok(10)
        assert log == ["got 5", "doubled to 10"]


class TestFlatten:
    """Tests for flatten method."""

    def test_flatten_ok_ok(self) -> None:
        nested: Result[Result[int, str], str] = Ok(Ok(42))
        assert nested.flatten() == Ok(42)

    def test_flatten_ok_err(self) -> None:
        nested: Result[Result[int, str], str] = Ok(Err("inner error"))
        assert nested.flatten() == Err("inner error")

    def test_flatten_err(self) -> None:
        nested: Result[Result[int, str], str] = Err("outer error")
        assert nested.flatten() == Err("outer error")

    def test_flatten_deeply_nested(self) -> None:
        # Flatten only removes one level
        inner: Result[int, str] = Ok(42)
        middle: Result[Result[int, str], str] = Ok(inner)
        deep: Result[Result[Result[int, str], str], str] = Ok(middle)
        once = deep.flatten()
        assert once == Ok(Ok(42))
        twice = once.flatten()
        assert twice == Ok(42)


class TestSequenceResults:
    """Tests for sequence_results and traverse_results functions."""

    def test_sequence_results_results_all_ok(self) -> None:
        results = [Ok(1), Ok(2), Ok(3)]
        assert sequence_results(results) == Ok([1, 2, 3])

    def test_sequence_results_fails_fast_on_err(self) -> None:
        results: list[Result[int, str]] = [Ok(1), Err("error"), Ok(3)]
        assert sequence_results(results) == Err("error")

    def test_sequence_results_returns_first_err(self) -> None:
        results: list[Result[int, str]] = [Ok(1), Err("first"), Err("second")]
        assert sequence_results(results) == Err("first")

    def test_sequence_results_empty_list(self) -> None:
        results: list[Result[int, str]] = []
        assert sequence_results(results) == Ok([])

    def test_sequence_results_with_generator(self) -> None:
        def gen() -> Iterable[Result[int, str]]:
            yield Ok(1)
            yield Ok(2)
            yield Ok(3)

        assert sequence_results(gen()) == Ok([1, 2, 3])

    def test_traverse_results_all_ok(self) -> None:
        items = [1, 2, 3]
        result = traverse_results(items, lambda x: Ok(x * 2))
        assert result == Ok([2, 4, 6])

    def test_traverse_results_fails_fast(self) -> None:
        items = [1, 2, 3]

        def maybe_fail(x: int) -> Result[int, str]:
            if x == 2:
                return Err("failed on 2")
            return Ok(x * 2)

        assert traverse_results(items, maybe_fail) == Err("failed on 2")

    def test_traverse_results_empty_list(self) -> None:
        items: list[int] = []
        result = traverse_results(items, lambda x: Ok(x * 2))
        assert result == Ok([])


class TestSplit:
    """Tests for Go-style split method."""

    def test_split_ok_returns_value_none(self) -> None:
        value, err = Ok(42).split()
        assert value == 42
        assert err is None

    def test_split_err_returns_none_error(self) -> None:
        value, err = Err("error").split()
        assert value is None
        assert err == "error"

    def test_split_go_style_pattern(self) -> None:
        def divide(a: int, b: int) -> Result[float, str]:
            if b == 0:
                return Err("division by zero")
            return Ok(a / b)

        # Success case
        value, err = divide(10, 2).split()
        if err is not None:
            pytest.fail("Should not have error")
        assert value == 5.0

        # Error case
        value, err = divide(10, 0).split()
        if err is not None:
            assert err == "division by zero"
        else:
            pytest.fail("Should have error")

    def test_split_with_none_value(self) -> None:
        value, err = Ok(None).split()
        assert value is None
        assert err is None

    def test_split_with_none_error(self) -> None:
        value, err = Err(None).split()
        assert value is None
        assert err is None


class TestResultTypeInference:
    """Tests for basic Result type inference."""

    def test_ok_type_annotated(self) -> None:
        ok: Ok[int] = Ok(42)
        assert_type(ok, Ok[int])

    def test_ok_with_string_annotated(self) -> None:
        ok: Ok[str] = Ok("hello")
        assert_type(ok, Ok[str])

    def test_err_type_annotated(self) -> None:
        err: Err[str] = Err("error")
        assert_type(err, Err[str])

    def test_err_with_int_annotated(self) -> None:
        err: Err[int] = Err(404)
        assert_type(err, Err[int])

    def test_result_union_ok(self) -> None:
        result: Result[int, str] = Ok(42)
        # Type checker narrows to Ok[int] but we annotated as Result[int, str]
        assert_type(result, Ok[int])

    def test_result_union_err(self) -> None:
        result: Result[int, str] = Err("error")
        # Type checker narrows to Err[str] but we annotated as Result[int, str]
        assert_type(result, Err[str])


class TestMapTypes:
    """Tests for type transformations in map operations."""

    def test_map_transforms_ok_type(self) -> None:
        result: Ok[int] = Ok(42)
        mapped = result.map(str)
        assert_type(mapped, Ok[str])

    def test_map_on_ok_directly_annotated(self) -> None:
        result: Ok[int] = Ok(42)
        mapped = result.map(str)
        assert_type(mapped, Ok[str])

    def test_map_err_transforms_err_type(self) -> None:
        result: Err[str] = Err("error")
        mapped = result.map_err(len)
        assert_type(mapped, Err[int])

    def test_map_err_on_err_directly_annotated(self) -> None:
        result: Err[str] = Err("error")
        mapped = result.map_err(len)
        assert_type(mapped, Err[int])

    def test_map_or_return_type(self) -> None:
        result: Result[int, str] = Ok(42)
        value = result.map_or("default", str)
        assert_type(value, str)

    def test_map_or_else_return_type(self) -> None:
        def error_handler(e: str) -> str:
            return f"error: {e}"

        result: Result[int, str] = Ok(42)
        value = result.map_or_else(error_handler, str)
        assert_type(value, str)


class TestChainTypes:
    """Tests for type transformations in chain operations."""

    def test_and_then_type(self) -> None:
        def to_string(x: int) -> Ok[str] | Err[str]:
            return Ok(str(x))

        result: Ok[int] = Ok(42)
        chained = result.and_then(to_string)
        assert_type(chained, Ok[str] | Err[str])

    def test_or_else_type(self) -> None:
        def recover(e: str) -> Ok[int] | Err[int]:
            return Ok(len(e))

        result: Err[str] = Err("error")
        recovered = result.or_else(recover)
        assert_type(recovered, Ok[int] | Err[int])


class TestUnwrapTypes:
    """Tests for unwrap method return types."""

    def test_unwrap_returns_t(self) -> None:
        result: Result[int, str] = Ok(42)
        value = result.unwrap()
        assert_type(value, int)

    def test_unwrap_err_returns_e(self) -> None:
        result: Result[int, str] = Err("error")
        error = result.unwrap_err()
        assert_type(error, str)

    def test_ok_method_returns_some(self) -> None:
        from unwrappy import Some

        # Ok.ok() now returns Some[T] for type safety
        result: Ok[int] = Ok(42)
        value = result.ok()
        assert_type(value, Some[int])

    def test_err_method_returns_some(self) -> None:
        from unwrappy import Some

        # Err.err() now returns Some[E] for type safety
        result: Err[str] = Err("error")
        error = result.err()
        assert_type(error, Some[str])

    def test_unwrap_or_returns_t(self) -> None:
        result: Result[int, str] = Ok(42)
        value = result.unwrap_or(0)
        assert_type(value, int)

    def test_unwrap_or_else_returns_t(self) -> None:
        result: Result[int, str] = Ok(42)
        value = result.unwrap_or_else(lambda e: 0)
        assert_type(value, int)

    def test_expect_returns_t(self) -> None:
        result: Result[int, str] = Ok(42)
        value = result.expect("should not fail")
        assert_type(value, int)

    def test_expect_err_returns_e(self) -> None:
        result: Result[int, str] = Err("error")
        error = result.expect_err("should not fail")
        assert_type(error, str)


class TestAsyncTypes:
    """Tests for async method return types.

    Note: These tests verify behavior by awaiting the coroutines,
    as direct coroutine type assertions have variance issues.
    """

    async def test_map_async_return_type(self) -> None:
        async def async_str(x: int) -> str:
            return str(x)

        result: Ok[int] = Ok(42)
        awaited = await result.map_async(async_str)
        assert_type(awaited, Ok[str])

    async def test_map_err_async_return_type(self) -> None:
        async def async_len(s: str) -> int:
            return len(s)

        result: Ok[int] = Ok(42)
        awaited = await result.map_err_async(async_len)
        assert_type(awaited, Ok[int])

    async def test_and_then_async_return_type(self) -> None:
        async def async_to_string(x: int) -> Ok[str] | Err[str]:
            return Ok(str(x))

        result: Ok[int] = Ok(42)
        awaited = await result.and_then_async(async_to_string)
        assert_type(awaited, Ok[str] | Err[str])

    async def test_or_else_async_return_type(self) -> None:
        async def async_recover(e: str) -> Ok[int] | Err[int]:
            return Ok(len(e))

        result: Err[str] = Err("error")
        awaited = await result.or_else_async(async_recover)
        assert_type(awaited, Ok[int] | Err[int])


class TestPredicateTypes:
    """Tests for predicate method return types."""

    def test_is_ok_returns_literal_true(self) -> None:
        # Ok.is_ok() returns Literal[True] for precise type narrowing
        result: Ok[int] = Ok(42)
        is_ok = result.is_ok()
        assert_type(is_ok, Literal[True])

    def test_is_err_returns_literal_true(self) -> None:
        # Err.is_err() returns Literal[True] for precise type narrowing
        result: Err[str] = Err("error")
        is_err = result.is_err()
        assert_type(is_err, Literal[True])


class TestLazyResultFactory:
    """Tests for LazyResult factory methods."""

    async def test_ok_creates_lazy_with_ok(self) -> None:
        result = await LazyResult.ok(42).collect()
        assert result == Ok(42)

    async def test_err_creates_lazy_with_err(self) -> None:
        result = await LazyResult.err("error").collect()
        assert result == Err("error")

    async def test_from_result_wraps_ok(self) -> None:
        result = await LazyResult.from_result(Ok(42)).collect()
        assert result == Ok(42)

    async def test_from_result_wraps_err(self) -> None:
        result = await LazyResult.from_result(Err("error")).collect()
        assert result == Err("error")

    async def test_from_awaitable_wraps_coroutine(self) -> None:
        async def async_ok() -> Result[int, str]:
            return Ok(42)

        result = await LazyResult.from_awaitable(async_ok()).collect()
        assert result == Ok(42)

    async def test_from_awaitable_wraps_err_coroutine(self) -> None:
        async def async_err() -> Result[int, str]:
            return Err("async error")

        result = await LazyResult.from_awaitable(async_err()).collect()
        assert result == Err("async error")


class TestLazyResultMap:
    """Tests for LazyResult.map()."""

    async def test_map_sync_on_ok(self) -> None:
        result = await LazyResult.ok(5).map(lambda x: x * 2).collect()
        assert result == Ok(10)

    async def test_map_sync_on_err_skips(self) -> None:
        called = False

        def should_not_call(x: int) -> int:
            nonlocal called
            called = True
            return x * 2

        result = await LazyResult.err("error").map(should_not_call).collect()
        assert result == Err("error")
        assert called is False

    async def test_map_async_on_ok(self) -> None:
        async def async_double(x: int) -> int:
            return x * 2

        result = await LazyResult.ok(5).map(async_double).collect()
        assert result == Ok(10)

    async def test_map_async_on_err_skips(self) -> None:
        called = False

        async def should_not_call(x: int) -> int:
            nonlocal called
            called = True
            return x * 2

        result = await LazyResult.err("error").map(should_not_call).collect()
        assert result == Err("error")
        assert called is False

    async def test_map_chain_multiple(self) -> None:
        result = await LazyResult.ok(2).map(lambda x: x + 1).map(lambda x: x * 2).collect()
        assert result == Ok(6)  # (2 + 1) * 2


class TestLazyResultMapErr:
    """Tests for LazyResult.map_err()."""

    async def test_map_err_sync_on_err(self) -> None:
        result = await LazyResult.err("error").map_err(str.upper).collect()
        assert result == Err("ERROR")

    async def test_map_err_sync_on_ok_skips(self) -> None:
        called = False

        def should_not_call(e: str) -> str:
            nonlocal called
            called = True
            return e.upper()

        result = await LazyResult.ok(42).map_err(should_not_call).collect()
        assert result == Ok(42)
        assert called is False

    async def test_map_err_async_on_err(self) -> None:
        async def async_upper(e: str) -> str:
            return e.upper()

        result = await LazyResult.err("error").map_err(async_upper).collect()
        assert result == Err("ERROR")


class TestLazyResultAndThen:
    """Tests for LazyResult.and_then()."""

    async def test_and_then_sync_on_ok_returns_ok(self) -> None:
        result = await LazyResult.ok(5).and_then(lambda x: Ok(x * 2)).collect()
        assert result == Ok(10)

    async def test_and_then_sync_on_ok_returns_err(self) -> None:
        result = await LazyResult.ok(5).and_then(lambda x: Err("failed")).collect()
        assert result == Err("failed")

    async def test_and_then_sync_on_err_skips(self) -> None:
        called = False

        def should_not_call(x: int) -> Ok[int] | Err[str]:
            nonlocal called
            called = True
            return Ok(x * 2)

        # Explicitly type the LazyResult to avoid literal type issues
        lazy: LazyResult[int, str] = LazyResult.err("error")
        result = await lazy.and_then(should_not_call).collect()  # ty:ignore[invalid-argument-type]
        assert result == Err("error")
        assert called is False

    async def test_and_then_async_on_ok(self) -> None:
        async def async_double(x: int) -> Result[int, str]:
            return Ok(x * 2)

        result = await LazyResult.ok(5).and_then(async_double).collect()
        assert result == Ok(10)

    async def test_and_then_async_returns_err(self) -> None:
        async def async_fail(x: int) -> Result[int, str]:
            return Err("async failed")

        result = await LazyResult.ok(5).and_then(async_fail).collect()
        assert result == Err("async failed")


class TestLazyResultOrElse:
    """Tests for LazyResult.or_else()."""

    async def test_or_else_sync_on_err_returns_ok(self) -> None:
        result = await LazyResult.err("error").or_else(lambda e: Ok(len(e))).collect()
        assert result == Ok(5)  # len("error")

    async def test_or_else_sync_on_err_returns_err(self) -> None:
        result = await LazyResult.err("error").or_else(lambda e: Err(f"new: {e}")).collect()
        assert result == Err("new: error")

    async def test_or_else_sync_on_ok_skips(self) -> None:
        called = False

        def should_not_call(e: str) -> Ok[int] | Err[str]:
            nonlocal called
            called = True
            return Ok(0)

        # Explicitly type the LazyResult to avoid literal type issues
        lazy: LazyResult[int, str] = LazyResult.ok(42)
        result = await lazy.or_else(should_not_call).collect()  # ty:ignore[invalid-argument-type]
        assert result == Ok(42)
        assert called is False

    async def test_or_else_async_on_err(self) -> None:
        async def async_recover(e: str) -> Result[int, str]:
            return Ok(len(e))

        result = await LazyResult.err("error").or_else(async_recover).collect()
        assert result == Ok(5)


class TestLazyResultTee:
    """Tests for LazyResult.tee() and inspect()."""

    async def test_tee_sync_on_ok_calls_fn(self) -> None:
        called_with: list[int] = []
        result = await LazyResult.ok(42).tee(lambda x: called_with.append(x)).collect()
        assert result == Ok(42)
        assert called_with == [42]

    async def test_tee_sync_on_err_skips(self) -> None:
        called = False

        def should_not_call(x: int) -> None:
            nonlocal called
            called = True

        result = await LazyResult.err("error").tee(should_not_call).collect()
        assert result == Err("error")
        assert called is False

    async def test_tee_async_on_ok(self) -> None:
        called_with: list[int] = []

        async def async_log(x: int) -> None:
            called_with.append(x)

        result = await LazyResult.ok(42).tee(async_log).collect()
        assert result == Ok(42)
        assert called_with == [42]

    async def test_inspect_is_alias(self) -> None:
        assert LazyResult.inspect is LazyResult.tee


class TestLazyResultInspectErr:
    """Tests for LazyResult.inspect_err()."""

    async def test_inspect_err_sync_on_err_calls_fn(self) -> None:
        called_with: list[str] = []
        result = await LazyResult.err("error").inspect_err(lambda e: called_with.append(e)).collect()
        assert result == Err("error")
        assert called_with == ["error"]

    async def test_inspect_err_sync_on_ok_skips(self) -> None:
        called = False

        def should_not_call(e: str) -> None:
            nonlocal called
            called = True

        result = await LazyResult.ok(42).inspect_err(should_not_call).collect()
        assert result == Ok(42)
        assert called is False

    async def test_inspect_err_async_on_err(self) -> None:
        called_with: list[str] = []

        async def async_log(e: str) -> None:
            called_with.append(e)

        result = await LazyResult.err("error").inspect_err(async_log).collect()
        assert result == Err("error")
        assert called_with == ["error"]


class TestLazyResultFlatten:
    """Tests for LazyResult.flatten()."""

    async def test_flatten_ok_ok(self) -> None:
        result = await LazyResult.ok(Ok(42)).flatten().collect()
        assert result == Ok(42)

    async def test_flatten_ok_err(self) -> None:
        result = await LazyResult.ok(Err("inner")).flatten().collect()
        assert result == Err("inner")

    async def test_flatten_err(self) -> None:
        lazy: LazyResult[Result[int, str], str] = LazyResult.err("outer")
        result = await lazy.flatten().collect()
        assert result == Err("outer")


class TestLazyResultChaining:
    """Tests for complex chains."""

    async def test_complex_sync_chain(self) -> None:
        log: list[str] = []
        result = await (
            LazyResult.ok(5)
            .tee(lambda x: log.append(f"start: {x}"))
            .map(lambda x: x * 2)
            .tee(lambda x: log.append(f"doubled: {x}"))
            .map(str)
            .tee(lambda x: log.append(f"stringified: {x}"))
            .collect()
        )
        assert result == Ok("10")
        assert log == ["start: 5", "doubled: 10", "stringified: 10"]

    async def test_complex_async_chain(self) -> None:
        async def async_double(x: int) -> int:
            return x * 2

        async def async_validate(x: int) -> Result[int, str]:
            if x > 0:
                return Ok(x)
            return Err("must be positive")

        result = await (
            LazyResult.ok(5)
            .map(async_double)
            .and_then(async_validate)  # ty: ignore[invalid-argument-type]
            .collect()
        )
        assert result == Ok(10)

    async def test_mixed_sync_async_chain(self) -> None:
        async def async_double(x: int) -> int:
            return x * 2

        result = await (
            LazyResult.ok(5)
            .map(lambda x: x + 1)  # Sync
            .map(async_double)  # Async
            .map(str)  # Sync
            .collect()
        )
        assert result == Ok("12")  # (5 + 1) * 2 = 12

    async def test_short_circuit_on_err(self) -> None:
        call_count = 0

        def increment(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + 1

        result = await (
            LazyResult.ok(5)
            .map(increment)  # Called
            .and_then(lambda x: Err("fail"))  # Short-circuits here
            .map(increment)  # Not called
            .map(increment)  # Not called
            .collect()
        )
        assert result == Err("fail")
        assert call_count == 1

    async def test_recovery_with_or_else(self) -> None:
        result = await (
            LazyResult.ok(5)
            .and_then(lambda x: Err("failed"))  # Fails
            .map(lambda x: x * 100)  # Skipped
            .or_else(lambda e: Ok(0))  # Recovers
            .map(lambda x: x + 1)  # Runs on recovered value
            .collect()
        )
        assert result == Ok(1)

    async def test_multiple_or_else(self) -> None:
        result = await (
            LazyResult.err("first")
            .or_else(lambda e: Err("second"))  # Still Err
            .or_else(lambda e: Ok(42))  # Recovers
            .collect()
        )
        assert result == Ok(42)


class TestLazyResultFromAwaitable:
    """Tests for LazyResult.from_awaitable()."""

    async def test_from_async_function_ok(self) -> None:
        async def fetch_data() -> Result[int, str]:
            return Ok(42)

        result = await LazyResult.from_awaitable(fetch_data()).collect()
        assert result == Ok(42)

    async def test_from_async_function_err(self) -> None:
        async def fetch_data() -> Result[int, str]:
            return Err("network error")

        result = await LazyResult.from_awaitable(fetch_data()).collect()
        assert result == Err("network error")

    async def test_chain_from_awaitable(self) -> None:
        async def fetch_user(id: int) -> Result[dict[str, str], str]:
            return Ok({"name": "Alice", "id": str(id)})

        result = await LazyResult.from_awaitable(fetch_user(42)).map(lambda u: u["name"]).map(str.upper).collect()
        assert result == Ok("ALICE")


class TestResultLazyMethod:
    """Tests for Result.lazy() conversion method."""

    async def test_ok_lazy_returns_lazy_result(self) -> None:
        lazy = Ok(42).lazy()
        assert isinstance(lazy, LazyResult)
        result = await lazy.collect()
        assert result == Ok(42)

    async def test_err_lazy_returns_lazy_result(self) -> None:
        lazy = Err("error").lazy()
        assert isinstance(lazy, LazyResult)
        result = await lazy.collect()
        assert result == Err("error")

    async def test_lazy_chain_and_collect(self) -> None:
        result = await Ok(5).lazy().map(lambda x: x * 2).map(str).collect()
        assert result == Ok("10")

    async def test_lazy_from_result_chain(self) -> None:
        initial: Result[int, str] = Ok(10)
        result = await (
            initial.lazy().and_then(lambda x: Ok(x + 5) if x > 0 else Err("negative")).map(lambda x: x * 2).collect()
        )
        assert result == Ok(30)  # (10 + 5) * 2


class TestLazyResultImmutability:
    """Tests for LazyResult immutability."""

    async def test_chain_creates_new_instance(self) -> None:
        lazy1 = LazyResult.ok(5)
        lazy2 = lazy1.map(lambda x: x * 2)
        lazy3 = lazy1.map(lambda x: x + 1)

        # All are different instances
        assert lazy1 is not lazy2
        assert lazy1 is not lazy3
        assert lazy2 is not lazy3

        # Each can be collected independently
        r1 = await lazy1.collect()
        r2 = await lazy2.collect()
        r3 = await lazy3.collect()

        assert r1 == Ok(5)
        assert r2 == Ok(10)
        assert r3 == Ok(6)

    async def test_reuse_lazy_base(self) -> None:
        base = LazyResult.ok(5).map(lambda x: x * 2)

        # Create two branches from the same base
        branch1 = base.map(lambda x: x + 1)
        branch2 = base.map(lambda x: x - 1)

        r1 = await branch1.collect()
        r2 = await branch2.collect()

        assert r1 == Ok(11)  # 5 * 2 + 1
        assert r2 == Ok(9)  # 5 * 2 - 1


class TestLazyResultTypes:
    """Type inference tests for LazyResult chain methods."""

    # Factory methods
    # Note: ty has known limitations with generic TypeVar inference (astral-sh/ty#501)
    # These assert_type tests document expected types but ty infers Unknown instead
    async def test_ok_type(self) -> None:
        lazy = LazyResult.ok(42)
        result = await lazy.collect()
        assert_type(result, Result[int, Any])  # ty: ignore[type-assertion-failure]

    async def test_err_type(self) -> None:
        lazy = LazyResult.err("error")
        result = await lazy.collect()
        assert_type(result, Result[Any, str])  # ty: ignore[type-assertion-failure]

    async def test_from_result_type(self) -> None:
        lazy = LazyResult.from_result(Ok(42))
        assert_type(lazy, LazyResult[int, Any])  # ty: ignore[type-assertion-failure]

    # map - transforms T to U, preserves E
    async def test_map_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        mapped = lazy.map(str)
        assert_type(mapped, LazyResult[str, str])  # ty: ignore[type-assertion-failure]

    async def test_map_chain_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        chained = lazy.map(str).map(len)
        assert_type(chained, LazyResult[int, str])  # ty: ignore[type-assertion-failure]

    # map_err - transforms E to F, preserves T
    async def test_map_err_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Err("error"))
        mapped = lazy.map_err(len)
        assert_type(mapped, LazyResult[int, int])  # ty: ignore[type-assertion-failure]

    # and_then - transforms T to U via Result[U, E]
    async def test_and_then_type(self) -> None:
        def to_string(x: int) -> Result[str, str]:
            return Ok(str(x))

        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        chained = lazy.and_then(to_string)
        assert_type(chained, LazyResult[str, str])  # ty: ignore[type-assertion-failure]

    # or_else - transforms E to F via Result[T, F]
    async def test_or_else_type(self) -> None:
        def recover(e: str) -> Result[int, int]:
            return Ok(len(e))

        lazy: LazyResult[int, str] = LazyResult.from_result(Err("error"))
        recovered = lazy.or_else(recover)
        assert_type(recovered, LazyResult[int, int])  # ty: ignore[type-assertion-failure]

    # tee - preserves T and E (side effect only)
    async def test_tee_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        teed = lazy.tee(print)
        assert_type(teed, LazyResult[int, str])  # ty: ignore[type-assertion-failure]

    # inspect (alias for tee)
    async def test_inspect_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        inspected = lazy.inspect(print)
        assert_type(inspected, LazyResult[int, str])  # ty: ignore[type-assertion-failure]

    # inspect_err - preserves T and E (side effect only)
    async def test_inspect_err_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Err("error"))
        inspected = lazy.inspect_err(print)
        assert_type(inspected, LazyResult[int, str])  # ty: ignore[type-assertion-failure]

    # flatten - Result[Result[U, E], E] -> Result[U, E]
    async def test_flatten_type(self) -> None:
        inner: Result[int, str] = Ok(42)
        lazy: LazyResult[Result[int, str], str] = LazyResult.from_result(Ok(inner))
        flattened = lazy.flatten()
        assert_type(flattened, LazyResult[int, str])  # ty: ignore[type-assertion-failure]

    # collect - LazyResult[T, E] -> Result[T, E]
    async def test_collect_type(self) -> None:
        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        result = await lazy.collect()
        assert_type(result, Result[int, str])  # ty: ignore[type-assertion-failure]

    # Complex chain preserves final types
    async def test_complex_chain_type(self) -> None:
        def validate(x: int) -> Result[str, str]:
            return Ok(str(x)) if x > 0 else Err("negative")

        lazy: LazyResult[int, str] = LazyResult.from_result(Ok(42))
        chained = lazy.map(lambda x: x * 2).and_then(validate).map(len)
        assert_type(chained, LazyResult[int, str])  # ty: ignore[type-assertion-failure]


class TestContext:
    """Tests for context() and with_context() error chaining."""

    def test_context_on_ok_returns_self(self) -> None:
        result = Ok(42).context("some context")
        assert result == Ok(42)

    def test_context_on_err_wraps_error(self) -> None:
        from unwrappy import ChainedError

        result = Err("original error").context("parsing config")
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ChainedError)
        assert str(error) == "parsing config: original error"

    def test_context_chaining(self) -> None:
        from unwrappy import ChainedError

        result = Err("invalid json").context("parsing config").context("loading settings")
        error = result.unwrap_err()
        assert isinstance(error, ChainedError)
        assert str(error) == "loading settings: parsing config: invalid json"

    def test_with_context_on_ok_skips_fn(self) -> None:
        called = False

        def lazy_context() -> str:
            nonlocal called
            called = True
            return "context"

        result = Ok(42).with_context(lazy_context)
        assert result == Ok(42)
        assert called is False  # Function not called for Ok

    def test_with_context_on_err_calls_fn(self) -> None:
        from unwrappy import ChainedError

        user_id = 123
        result = Err("not found").with_context(lambda: f"fetching user {user_id}")
        error = result.unwrap_err()
        assert isinstance(error, ChainedError)
        assert str(error) == "fetching user 123: not found"

    def test_chained_error_root_cause(self) -> None:
        from unwrappy import ChainedError

        result = Err("root").context("level1").context("level2")
        error = result.unwrap_err()
        assert isinstance(error, ChainedError)
        assert error.root_cause() == "root"

    def test_chained_error_chain(self) -> None:
        from unwrappy import ChainedError

        result = Err("root").context("level1").context("level2")
        error = result.unwrap_err()
        assert isinstance(error, ChainedError)
        assert error.chain() == ["level2", "level1"]


class TestFilter:
    """Tests for filter() method on Result."""

    def test_filter_ok_passes(self) -> None:
        result = Ok(5).filter(lambda x: x > 0, "must be positive")
        assert result == Ok(5)

    def test_filter_ok_fails(self) -> None:
        result = Ok(-1).filter(lambda x: x > 0, "must be positive")
        assert result == Err("must be positive")

    def test_filter_err_unchanged(self) -> None:
        result: Result[int, str] = Err("original error")
        filtered = result.filter(lambda x: x > 0, "validation failed")
        assert filtered == Err("original error")

    def test_filter_with_complex_predicate(self) -> None:
        def is_valid_email(s: str) -> bool:
            return "@" in s and "." in s

        result1 = Ok("user@example.com").filter(is_valid_email, "invalid email")
        assert result1 == Ok("user@example.com")

        result2 = Ok("invalid").filter(is_valid_email, "invalid email")
        assert result2 == Err("invalid email")


class TestZip:
    """Tests for zip() and zip_with() methods on Result."""

    def test_zip_ok_ok(self) -> None:
        result = Ok(1).zip(Ok("a"))
        assert result == Ok((1, "a"))

    def test_zip_ok_err(self) -> None:
        result = Ok(1).zip(Err("error"))
        assert result == Err("error")

    def test_zip_err_ok(self) -> None:
        result: Result[int, str] = Err("first error")
        zipped = result.zip(Ok(2))
        assert zipped == Err("first error")

    def test_zip_err_err(self) -> None:
        result: Result[int, str] = Err("first")
        zipped = result.zip(Err("second"))
        assert zipped == Err("first")  # First error wins

    def test_zip_with_ok_ok(self) -> None:
        result = Ok(2).zip_with(Ok(3), lambda a, b: a + b)
        assert result == Ok(5)

    def test_zip_with_ok_err(self) -> None:
        result = Ok(2).zip_with(Err("error"), lambda a, b: a + b)
        assert result == Err("error")

    def test_zip_with_err_ok(self) -> None:
        result: Result[int, str] = Err("error")
        zipped = result.zip_with(Ok(3), lambda a, b: a + b)
        assert zipped == Err("error")

    def test_zip_multiple(self) -> None:
        """Test chaining multiple zips."""
        a = Ok(1)
        b = Ok(2)
        c = Ok(3)

        result = a.zip(b).and_then(lambda t: Ok((*t, c.unwrap())))
        assert result == Ok((1, 2, 3))
