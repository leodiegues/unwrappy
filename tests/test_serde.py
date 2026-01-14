"""Tests for JSON serialization of Result and Option types."""

from __future__ import annotations

import json

import pytest

from unwrappy import NOTHING, Err, LazyOption, LazyResult, Ok, Option, Result, Some
from unwrappy.serde import (
    ResultDecoder,
    ResultEncoder,
    dumps,
    loads,
    result_decoder,
)


class TestResultEncoder:
    """Tests for ResultEncoder JSON encoder."""

    def test_encode_ok_with_int(self) -> None:
        result = json.dumps(Ok(42), cls=ResultEncoder)
        assert json.loads(result) == {"__unwrappy_type__": "Ok", "value": 42}

    def test_encode_ok_with_string(self) -> None:
        result = json.dumps(Ok("hello"), cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Ok"
        assert data["value"] == "hello"

    def test_encode_ok_with_none(self) -> None:
        result = json.dumps(Ok(None), cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Ok"
        assert data["value"] is None

    def test_encode_ok_with_dict(self) -> None:
        result = json.dumps(Ok({"key": "value"}), cls=ResultEncoder)
        data = json.loads(result)
        assert data["value"] == {"key": "value"}

    def test_encode_ok_with_list(self) -> None:
        result = json.dumps(Ok([1, 2, 3]), cls=ResultEncoder)
        data = json.loads(result)
        assert data["value"] == [1, 2, 3]

    def test_encode_ok_with_bool(self) -> None:
        for val in [True, False]:
            result = json.dumps(Ok(val), cls=ResultEncoder)
            data = json.loads(result)
            assert data["value"] is val

    def test_encode_ok_with_float(self) -> None:
        result = json.dumps(Ok(3.14159), cls=ResultEncoder)
        data = json.loads(result)
        assert data["value"] == 3.14159

    def test_encode_err_with_string(self) -> None:
        result = json.dumps(Err("error"), cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Err"
        assert data["error"] == "error"

    def test_encode_err_with_dict(self) -> None:
        result = json.dumps(Err({"code": 404, "msg": "not found"}), cls=ResultEncoder)
        data = json.loads(result)
        assert data["error"] == {"code": 404, "msg": "not found"}

    def test_encode_err_with_none(self) -> None:
        result = json.dumps(Err(None), cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Err"
        assert data["error"] is None

    def test_encode_lazy_result_raises(self) -> None:
        lazy = LazyResult.ok(42)
        with pytest.raises(TypeError) as exc_info:
            json.dumps(lazy, cls=ResultEncoder)
        assert "LazyResult" in str(exc_info.value)
        assert "collect()" in str(exc_info.value)

    def test_encode_lazy_result_with_ops_raises(self) -> None:
        lazy = LazyResult.ok(42).map(lambda x: x * 2)
        with pytest.raises(TypeError) as exc_info:
            json.dumps(lazy, cls=ResultEncoder)
        assert "LazyResult" in str(exc_info.value)

    def test_encode_nested_result_ok_ok(self) -> None:
        nested: Result[Result[int, str], str] = Ok(Ok(42))
        result = json.dumps(nested, cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Ok"
        assert data["value"]["__unwrappy_type__"] == "Ok"
        assert data["value"]["value"] == 42

    def test_encode_nested_result_ok_err(self) -> None:
        nested: Result[Result[int, str], str] = Ok(Err("inner"))
        result = json.dumps(nested, cls=ResultEncoder)
        data = json.loads(result)
        assert data["value"]["__unwrappy_type__"] == "Err"
        assert data["value"]["error"] == "inner"

    def test_encode_list_of_results(self) -> None:
        results = [Ok(1), Err("a"), Ok(3)]
        encoded = json.dumps(results, cls=ResultEncoder)
        data = json.loads(encoded)
        assert len(data) == 3
        assert data[0]["__unwrappy_type__"] == "Ok"
        assert data[1]["__unwrappy_type__"] == "Err"

    def test_encode_dict_with_result_values(self) -> None:
        data = {"success": Ok(42), "failure": Err("error")}
        encoded = json.dumps(data, cls=ResultEncoder)
        decoded = json.loads(encoded)
        assert decoded["success"]["__unwrappy_type__"] == "Ok"
        assert decoded["failure"]["__unwrappy_type__"] == "Err"


class TestResultDecoder:
    """Tests for result_decoder and ResultDecoder."""

    def test_decode_ok(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": 42}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Ok(42)

    def test_decode_ok_with_string(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": "hello"}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Ok("hello")

    def test_decode_ok_with_none(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": null}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Ok(None)
        assert result.unwrap() is None

    def test_decode_ok_with_list(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": [1, 2, 3]}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Ok([1, 2, 3])

    def test_decode_ok_with_dict(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": {"key": "value"}}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Ok({"key": "value"})

    def test_decode_err(self) -> None:
        json_str = '{"__unwrappy_type__": "Err", "error": "not found"}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Err("not found")

    def test_decode_err_with_dict(self) -> None:
        json_str = '{"__unwrappy_type__": "Err", "error": {"code": 500}}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Err({"code": 500})

    def test_decode_err_with_none(self) -> None:
        json_str = '{"__unwrappy_type__": "Err", "error": null}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Err(None)

    def test_decode_with_class(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": 42}'
        result = json.loads(json_str, cls=ResultDecoder)
        assert result == Ok(42)

    def test_decode_regular_dict_unchanged(self) -> None:
        json_str = '{"key": "value", "number": 42}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == {"key": "value", "number": 42}

    def test_decode_nested_result(self) -> None:
        json_str = """
        {
            "__unwrappy_type__": "Ok",
            "value": {
                "__unwrappy_type__": "Err",
                "error": "inner error"
            }
        }
        """
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Ok(Err("inner error"))

    def test_decode_unknown_type_unchanged(self) -> None:
        json_str = '{"__unwrappy_type__": "SomeOtherType", "data": 123}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == {"__unwrappy_type__": "SomeOtherType", "data": 123}

    def test_decode_list_of_results(self) -> None:
        json_str = """[
            {"__unwrappy_type__": "Ok", "value": 1},
            {"__unwrappy_type__": "Err", "error": "x"},
            {"__unwrappy_type__": "Ok", "value": 3}
        ]"""
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == [Ok(1), Err("x"), Ok(3)]

    def test_decode_dict_with_result_values(self) -> None:
        json_str = """{
            "success": {"__unwrappy_type__": "Ok", "value": 42},
            "failure": {"__unwrappy_type__": "Err", "error": "error"}
        }"""
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == {"success": Ok(42), "failure": Err("error")}


class TestConvenienceFunctions:
    """Tests for dumps() and loads() convenience functions."""

    def test_dumps_ok(self) -> None:
        result = dumps(Ok(42))
        assert '"__unwrappy_type__": "Ok"' in result
        assert '"value": 42' in result

    def test_dumps_err(self) -> None:
        result = dumps(Err("error"))
        assert '"__unwrappy_type__": "Err"' in result
        assert '"error": "error"' in result

    def test_loads_ok(self) -> None:
        json_str = '{"__unwrappy_type__": "Ok", "value": 42}'
        result = loads(json_str)
        assert result == Ok(42)

    def test_loads_err(self) -> None:
        json_str = '{"__unwrappy_type__": "Err", "error": "not found"}'
        result = loads(json_str)
        assert result == Err("not found")

    def test_roundtrip_ok(self) -> None:
        original = Ok({"nested": [1, 2, 3]})
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original

    def test_roundtrip_err(self) -> None:
        original = Err({"code": 500, "message": "server error"})
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original

    def test_roundtrip_nested(self) -> None:
        original: Result[Result[int, str], str] = Ok(Ok(42))
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original

    def test_dumps_with_indent(self) -> None:
        result = dumps(Ok(42), indent=2)
        assert "\n" in result

    def test_dumps_with_sort_keys(self) -> None:
        result = dumps(Ok({"b": 2, "a": 1}), sort_keys=True)
        assert result.index('"a"') < result.index('"b"')


class TestEdgeCases:
    """Edge case tests for JSON serialization."""

    def test_ok_with_empty_string(self) -> None:
        original = Ok("")
        decoded = loads(dumps(original))
        assert decoded == original
        assert decoded.unwrap() == ""

    def test_err_with_empty_string(self) -> None:
        original = Err("")
        decoded = loads(dumps(original))
        assert decoded == original
        assert decoded.unwrap_err() == ""

    def test_ok_with_empty_dict(self) -> None:
        original = Ok({})
        decoded = loads(dumps(original))
        assert decoded == original

    def test_ok_with_empty_list(self) -> None:
        original = Ok([])
        decoded = loads(dumps(original))
        assert decoded == original

    def test_ok_with_unicode(self) -> None:
        original = Ok("Hello \u4e16\u754c")
        decoded = loads(dumps(original))
        assert decoded == original

    def test_ok_with_zero(self) -> None:
        original = Ok(0)
        decoded = loads(dumps(original))
        assert decoded == original
        assert decoded.unwrap() == 0

    def test_ok_with_negative(self) -> None:
        original = Ok(-42)
        decoded = loads(dumps(original))
        assert decoded == original

    def test_deeply_nested_structure(self) -> None:
        original = Ok({"level1": {"level2": {"level3": [1, 2, 3]}}})
        decoded = loads(dumps(original))
        assert decoded == original

    def test_result_in_list_in_result(self) -> None:
        original = Ok([Ok(1), Err("x")])
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original
        inner_list = decoded.unwrap()
        assert inner_list[0] == Ok(1)
        assert inner_list[1] == Err("x")


class TestOptionEncoder:
    """Tests for Option type encoding."""

    def test_encode_some_with_int(self) -> None:
        result = json.dumps(Some(42), cls=ResultEncoder)
        assert json.loads(result) == {"__unwrappy_type__": "Some", "value": 42}

    def test_encode_some_with_string(self) -> None:
        result = json.dumps(Some("hello"), cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Some"
        assert data["value"] == "hello"

    def test_encode_some_with_none(self) -> None:
        result = json.dumps(Some(None), cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Some"
        assert data["value"] is None

    def test_encode_some_with_dict(self) -> None:
        result = json.dumps(Some({"key": "value"}), cls=ResultEncoder)
        data = json.loads(result)
        assert data["value"] == {"key": "value"}

    def test_encode_some_with_list(self) -> None:
        result = json.dumps(Some([1, 2, 3]), cls=ResultEncoder)
        data = json.loads(result)
        assert data["value"] == [1, 2, 3]

    def test_encode_nothing(self) -> None:
        result = json.dumps(NOTHING, cls=ResultEncoder)
        assert json.loads(result) == {"__unwrappy_type__": "Nothing"}

    def test_encode_lazy_option_raises(self) -> None:
        lazy = LazyOption.some(42)
        with pytest.raises(TypeError) as exc_info:
            json.dumps(lazy, cls=ResultEncoder)
        assert "LazyOption" in str(exc_info.value)
        assert "collect()" in str(exc_info.value)

    def test_encode_nested_option(self) -> None:
        nested: Option[Option[int]] = Some(Some(42))
        result = json.dumps(nested, cls=ResultEncoder)
        data = json.loads(result)
        assert data["__unwrappy_type__"] == "Some"
        assert data["value"]["__unwrappy_type__"] == "Some"
        assert data["value"]["value"] == 42

    def test_encode_list_of_options(self) -> None:
        options = [Some(1), NOTHING, Some(3)]
        encoded = json.dumps(options, cls=ResultEncoder)
        data = json.loads(encoded)
        assert len(data) == 3
        assert data[0]["__unwrappy_type__"] == "Some"
        assert data[1]["__unwrappy_type__"] == "Nothing"
        assert data[2]["__unwrappy_type__"] == "Some"


class TestOptionDecoder:
    """Tests for Option type decoding."""

    def test_decode_some(self) -> None:
        json_str = '{"__unwrappy_type__": "Some", "value": 42}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Some(42)

    def test_decode_some_with_string(self) -> None:
        json_str = '{"__unwrappy_type__": "Some", "value": "hello"}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Some("hello")

    def test_decode_some_with_none(self) -> None:
        json_str = '{"__unwrappy_type__": "Some", "value": null}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Some(None)
        assert result.unwrap() is None

    def test_decode_some_with_list(self) -> None:
        json_str = '{"__unwrappy_type__": "Some", "value": [1, 2, 3]}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Some([1, 2, 3])

    def test_decode_some_with_dict(self) -> None:
        json_str = '{"__unwrappy_type__": "Some", "value": {"key": "value"}}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Some({"key": "value"})

    def test_decode_nothing(self) -> None:
        json_str = '{"__unwrappy_type__": "Nothing"}'
        result = json.loads(json_str, object_hook=result_decoder)
        assert result is NOTHING

    def test_decode_nested_option(self) -> None:
        json_str = """
        {
            "__unwrappy_type__": "Some",
            "value": {
                "__unwrappy_type__": "Some",
                "value": 42
            }
        }
        """
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == Some(Some(42))

    def test_decode_list_of_options(self) -> None:
        json_str = """[
            {"__unwrappy_type__": "Some", "value": 1},
            {"__unwrappy_type__": "Nothing"},
            {"__unwrappy_type__": "Some", "value": 3}
        ]"""
        result = json.loads(json_str, object_hook=result_decoder)
        assert result == [Some(1), NOTHING, Some(3)]


class TestOptionConvenienceFunctions:
    """Tests for dumps() and loads() with Option types."""

    def test_dumps_some(self) -> None:
        result = dumps(Some(42))
        assert '"__unwrappy_type__": "Some"' in result
        assert '"value": 42' in result

    def test_dumps_nothing(self) -> None:
        result = dumps(NOTHING)
        assert '"__unwrappy_type__": "Nothing"' in result

    def test_loads_some(self) -> None:
        json_str = '{"__unwrappy_type__": "Some", "value": 42}'
        result = loads(json_str)
        assert result == Some(42)

    def test_loads_nothing(self) -> None:
        json_str = '{"__unwrappy_type__": "Nothing"}'
        result = loads(json_str)
        assert result is NOTHING

    def test_roundtrip_some(self) -> None:
        original = Some({"nested": [1, 2, 3]})
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original

    def test_roundtrip_nothing(self) -> None:
        encoded = dumps(NOTHING)
        decoded = loads(encoded)
        assert decoded is NOTHING

    def test_roundtrip_nested_option(self) -> None:
        original: Option[Option[int]] = Some(Some(42))
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original


class TestMixedResultOption:
    """Tests for mixing Result and Option in serialization."""

    def test_result_containing_option(self) -> None:
        original = Ok(Some(42))
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original
        assert decoded.unwrap() == Some(42)

    def test_option_containing_result(self) -> None:
        original = Some(Ok(42))
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original
        assert decoded.unwrap() == Ok(42)

    def test_list_of_mixed_types(self) -> None:
        original = [Ok(1), Some(2), Err("x"), NOTHING]
        encoded = dumps(original)
        decoded = loads(encoded)
        assert decoded == original
