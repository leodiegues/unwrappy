from __future__ import annotations

from unwrappy.exceptions import ChainedError
from unwrappy.option import (
    NOTHING,
    LazyOption,
    Nothing,
    Option,
    Some,
    from_nullable,
    sequence_options,
    traverse_options,
)
from unwrappy.result import Err, LazyResult, Ok, Result, sequence_results, traverse_results
from unwrappy.serde import ResultDecoder, ResultEncoder, dumps, loads, result_decoder

__all__ = [
    # Result types
    "Result",
    "Ok",
    "Err",
    "LazyResult",
    "sequence_results",
    "traverse_results",
    # Option types
    "Option",
    "Some",
    "Nothing",
    "NOTHING",
    "LazyOption",
    "sequence_options",
    "traverse_options",
    "from_nullable",
    # Errors
    "ChainedError",
    # Serialization
    "ResultEncoder",
    "ResultDecoder",
    "result_decoder",
    "dumps",
    "loads",
]
