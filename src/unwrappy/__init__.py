from __future__ import annotations

from importlib.metadata import version

from unwrappy.exceptions import ChainedError, UnwrapError
from unwrappy.option import (
    NOTHING,
    LazyOption,
    Nothing,
    Option,
    Some,
    from_nullable,
    is_nothing,
    is_some,
    sequence_options,
    traverse_options,
)
from unwrappy.result import Err, LazyResult, Ok, Result, is_err, is_ok, sequence_results, traverse_results
from unwrappy.serde import ResultDecoder, ResultEncoder, dumps, loads, result_decoder

__version__ = version("unwrappy")

__all__ = [
    # Result types
    "Result",
    "Ok",
    "Err",
    "LazyResult",
    "sequence_results",
    "traverse_results",
    "is_ok",
    "is_err",
    # Option types
    "Option",
    "Some",
    "Nothing",
    "NOTHING",
    "LazyOption",
    "sequence_options",
    "traverse_options",
    "from_nullable",
    "is_some",
    "is_nothing",
    # Errors
    "UnwrapError",
    "ChainedError",
    # Serialization
    "ResultEncoder",
    "ResultDecoder",
    "result_decoder",
    "dumps",
    "loads",
    # Version
    "__version__",
]
