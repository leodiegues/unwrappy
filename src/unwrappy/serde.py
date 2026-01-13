"""JSON serialization support for Result types.

This module provides JSON encoder/decoder support for Ok and Err types.
It uses a tagged format for unambiguous round-trip serialization.

Format:
    Ok(value)  -> {"__unwrappy_type__": "Ok", "value": <value>}
    Err(error) -> {"__unwrappy_type__": "Err", "error": <error>}

Example:
    >>> import json
    >>> from unwrappy import Ok, Err
    >>> from unwrappy.serde import ResultEncoder, result_decoder

    >>> # Encoding
    >>> json.dumps(Ok(42), cls=ResultEncoder)
    '{"__unwrappy_type__": "Ok", "value": 42}'

    >>> # Decoding
    >>> json.loads('{"__unwrappy_type__": "Ok", "value": 42}', object_hook=result_decoder)
    Ok(42)

    >>> # Round-trip
    >>> original = Err("not found")
    >>> encoded = json.dumps(original, cls=ResultEncoder)
    >>> decoded = json.loads(encoded, object_hook=result_decoder)
    >>> decoded == original
    True
"""

from __future__ import annotations

import json
from typing import Any

from unwrappy.result import Err, LazyResult, Ok

_TYPE_KEY = "__unwrappy_type__"


class ResultEncoder(json.JSONEncoder):
    """JSON encoder for Result types.

    Extends json.JSONEncoder to handle Ok and Err types.
    Nested Result types are handled recursively.

    Example:
        >>> import json
        >>> from unwrappy import Ok
        >>> from unwrappy.serde import ResultEncoder
        >>> json.dumps(Ok({"key": "value"}), cls=ResultEncoder)
        '{"__unwrappy_type__": "Ok", "value": {"key": "value"}}'
    """

    def default(self, o: Any) -> Any:
        """Encode Result types to JSON-serializable dict.

        Args:
            o: Object to encode.

        Returns:
            JSON-serializable representation.

        Raises:
            TypeError: If o is a LazyResult.
        """
        if isinstance(o, Ok):
            return {_TYPE_KEY: "Ok", "value": o.unwrap()}

        if isinstance(o, Err):
            return {_TYPE_KEY: "Err", "error": o.unwrap_err()}

        if isinstance(o, LazyResult):
            raise TypeError(
                "Cannot JSON serialize LazyResult. "
                "Call .collect() first to obtain a concrete Result, then serialize that."
            )

        return super().default(o)


def result_decoder(dct: dict[str, Any]) -> Any:
    """JSON object hook to decode Result types.

    Use as the object_hook parameter to json.loads().

    Args:
        dct: Dictionary from JSON parsing.

    Returns:
        Decoded Result type if applicable, otherwise the original dict.

    Example:
        >>> import json
        >>> from unwrappy.serde import result_decoder
        >>> json.loads('{"__unwrappy_type__": "Ok", "value": 42}', object_hook=result_decoder)
        Ok(42)
    """
    if _TYPE_KEY not in dct:
        return dct

    type_name = dct[_TYPE_KEY]

    if type_name == "Ok":
        return Ok(dct["value"])

    if type_name == "Err":
        return Err(dct["error"])

    return dct


class ResultDecoder(json.JSONDecoder):
    """JSON decoder for Result types.

    Alternative to using object_hook with result_decoder.
    Useful when you want a standalone decoder class.

    Example:
        >>> import json
        >>> from unwrappy.serde import ResultDecoder
        >>> json.loads('{"__unwrappy_type__": "Err", "error": "not found"}', cls=ResultDecoder)
        Err('not found')
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs["object_hook"] = result_decoder
        super().__init__(**kwargs)


def dumps(obj: Any, **kwargs: Any) -> str:
    """Serialize obj to JSON string with Result type support.

    Convenience wrapper around json.dumps with ResultEncoder.

    Args:
        obj: Object to serialize.
        **kwargs: Additional arguments passed to json.dumps.

    Returns:
        JSON string.

    Example:
        >>> from unwrappy import Ok
        >>> from unwrappy.serde import dumps
        >>> dumps(Ok(42))
        '{"__unwrappy_type__": "Ok", "value": 42}'
    """
    return json.dumps(obj, cls=ResultEncoder, **kwargs)


def loads(s: str, **kwargs: Any) -> Any:
    """Deserialize JSON string with Result type support.

    Convenience wrapper around json.loads with result_decoder.

    Args:
        s: JSON string to deserialize.
        **kwargs: Additional arguments passed to json.loads.

    Returns:
        Deserialized object with Result types restored.

    Example:
        >>> from unwrappy.serde import loads
        >>> loads('{"__unwrappy_type__": "Ok", "value": 42}')
        Ok(42)
    """
    return json.loads(s, object_hook=result_decoder, **kwargs)
